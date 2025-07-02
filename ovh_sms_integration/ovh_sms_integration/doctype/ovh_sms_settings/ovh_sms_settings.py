# Code OVH SMS Settings - Version complète avec toutes les méthodes nécessaires

import frappe
import requests
import hashlib
import datetime
import json
import re
import time
from frappe.model.document import Document
from frappe import _

class OVHSMSSettings(Document):
	def validate(self):
		if self.enabled:
			if not self.application_key:
				frappe.throw(_("Application Key est requis"))
			if not self.get_password("application_secret"):
				frappe.throw(_("Application Secret est requis"))
			if not self.get_password("consumer_key"):
				frappe.throw(_("Consumer Key est requis"))
			if not self.auto_detect_service and not self.service_name:
				frappe.throw(_("Service Name est requis si la détection automatique est désactivée"))

	def get_decrypted_password(self, fieldname):
		"""Récupère et décrypte un champ de type Password"""
		try:
			# Méthode 1 : get_password (recommandée pour les champs Password)
			password_value = self.get_password(fieldname)
			if password_value:
				return password_value.strip()
			
			# Méthode 2 : Récupération directe
			direct_value = self.get(fieldname)
			if direct_value:
				return str(direct_value).strip()
			
			return None
			
		except Exception as e:
			frappe.log_error(f"Erreur récupération password {fieldname}: {str(e)}")
			return None

	def _get_ovh_server_time(self):
		"""Récupère le temps synchronisé du serveur OVH"""
		try:
			response = requests.get("https://eu.api.ovh.com/1.0/auth/time", timeout=10)
			if response.status_code == 200:
				return int(response.text.strip())
		except:
			pass
		# Fallback sur temps local
		return int(time.time())

	def _create_signature(self, method, url, body=""):
		"""Crée la signature OVH"""
		try:
			timestamp = str(self._get_ovh_server_time())
			
			app_secret = self.get_decrypted_password("application_secret")
			consumer_key = self.get_decrypted_password("consumer_key")
			
			if not app_secret:
				raise ValueError("Application Secret vide")
			if not consumer_key:
				raise ValueError("Consumer Key vide")
			
			# Construire la chaîne de hachage selon la doc OVH
			pre_hash = f"{app_secret}+{consumer_key}+{method}+{url}+{body}+{timestamp}"
			
			# Calculer le hash SHA1
			sha1_hash = hashlib.sha1(pre_hash.encode('utf-8')).hexdigest()
			signature = f"$1${sha1_hash}"
			
			return {
				"signature": signature,
				"timestamp": timestamp
			}
			
		except Exception as e:
			frappe.log_error(f"Erreur création signature OVH: {str(e)}")
			raise

	def _make_ovh_request(self, method, endpoint, body=""):
		"""Effectue une requête OVH"""
		url = f"https://eu.api.ovh.com/1.0{endpoint}"
		
		try:
			signature_data = self._create_signature(method, url, body)
			consumer_key = self.get_decrypted_password("consumer_key")
			
			headers = {
				"X-Ovh-Application": str(self.application_key).strip(),
				"X-Ovh-Consumer": consumer_key,
				"X-Ovh-Signature": signature_data["signature"],
				"X-Ovh-Timestamp": signature_data["timestamp"]
			}
			
			if method.upper() in ["POST", "PUT"]:
				headers["Content-Type"] = "application/json"
			
			if method.upper() == "GET":
				response = requests.get(url, headers=headers, timeout=30)
			elif method.upper() == "POST":
				response = requests.post(url, data=body, headers=headers, timeout=30)
			else:
				raise ValueError(f"Méthode HTTP non supportée: {method}")
			
			response.raise_for_status()
			return response.json()
			
		except requests.exceptions.HTTPError as e:
			error_msg = f"Erreur HTTP {e.response.status_code}: {e.response.reason}"
			try:
				error_detail = e.response.json()
				if error_detail.get('message'):
					error_msg += f" - {error_detail['message']}"
			except:
				pass
			
			frappe.log_error(error_msg)
			raise Exception(error_msg)
			
		except Exception as e:
			frappe.log_error(f"Erreur requête OVH: {str(e)}")
			raise

	def get_service_name(self):
		"""Récupère le nom du service SMS"""
		try:
			if not self.auto_detect_service and self.service_name:
				return self.service_name
			
			services = self._make_ovh_request("GET", "/sms")
			if services:
				return services[0]
			else:
				frappe.throw(_("Aucun service SMS trouvé"))
		except Exception as e:
			frappe.throw(_("Erreur services SMS: {0}").format(str(e)))

	def get_service_details(self, service_name):
		"""Récupère les détails d'un service SMS"""
		try:
			return self._make_ovh_request("GET", f"/sms/{service_name}")
		except Exception as e:
			frappe.log_error(f"Erreur récupération détails service {service_name}: {e}")
			raise

	def get_available_senders(self):
		"""Récupère la liste des expéditeurs disponibles"""
		try:
			service_name = self.get_service_name()
			return self._make_ovh_request("GET", f"/sms/{service_name}/senders")
		except Exception as e:
			frappe.log_error(f"Erreur récupération expéditeurs: {e}")
			return []

	def create_sender(self, sender_name, description="ERPNext Sender"):
		"""Crée un nouvel expéditeur SMS"""
		try:
			service_name = self.get_service_name()
			
			# Validation du nom de l'expéditeur
			if not re.match(r'^[a-zA-Z0-9]{1,11}$', sender_name):
				raise ValueError("Le nom de l'expéditeur doit contenir uniquement des caractères alphanumériques (max 11 caractères)")
			
			body_data = {
				"sender": sender_name,
				"description": description
			}
			
			body = json.dumps(body_data, separators=(',', ':'))
			result = self._make_ovh_request("POST", f"/sms/{service_name}/senders", body)
			
			frappe.logger().info(f"Expéditeur SMS créé: {sender_name}")
			
			return {
				"success": True,
				"message": f"Expéditeur '{sender_name}' créé avec succès",
				"details": result
			}
			
		except Exception as e:
			error_msg = f"Erreur création expéditeur: {str(e)}"
			frappe.log_error(error_msg)
			return {
				"success": False,
				"message": error_msg
			}

	def validate_and_create_sender(self, sender):
		"""Valide un expéditeur et le crée si nécessaire"""
		try:
			available_senders = self.get_available_senders()
			
			if sender in available_senders:
				return {
					"success": True,
					"message": f"Expéditeur '{sender}' disponible",
					"created": False
				}
			
			result = self.create_sender(sender)
			if result["success"]:
				result["created"] = True
			
			return result
			
		except Exception as e:
			return {
				"success": False,
				"message": f"Erreur validation expéditeur: {str(e)}",
				"created": False
			}

	def get_best_sender(self):
		"""Retourne le meilleur expéditeur disponible ou en crée un"""
		try:
			# D'abord, essayer l'expéditeur par défaut configuré
			if self.default_sender:
				result = self.validate_and_create_sender(self.default_sender)
				if result["success"]:
					return self.default_sender
			
			# Sinon, récupérer les expéditeurs disponibles
			available_senders = self.get_available_senders()
			
			if available_senders:
				return available_senders[0]
			
			# Aucun expéditeur disponible, créer un expéditeur par défaut
			default_names = ["ERPNext", "ERP", "System", "SMS", "Info"]
			
			for name in default_names:
				result = self.create_sender(name)
				if result["success"]:
					return name
			
			frappe.throw(_("Impossible de créer un expéditeur SMS valide"))
			
		except Exception as e:
			frappe.log_error(f"Erreur récupération expéditeur: {e}")
			return "ERPNext"  # Fallback

	def send_sms(self, message, phone_number, sender=None):
		"""Envoie un SMS via l'API OVH"""
		try:
			service_name = self.get_service_name()
			
			# Déterminer l'expéditeur à utiliser
			if not sender:
				sender = self.get_best_sender()
			else:
				# Valider l'expéditeur fourni
				result = self.validate_and_create_sender(sender)
				if not result["success"]:
					frappe.logger().warning(f"Impossible d'utiliser l'expéditeur {sender}, fallback automatique")
					sender = self.get_best_sender()
			
			# Préparation du corps de la requête
			body_data = {
				"message": message,
				"receivers": [phone_number],
				"sender": sender,
				"noStopClause": False,
				"priority": "high"
			}
			
			body = json.dumps(body_data, separators=(',', ':'))
			result = self._make_ovh_request("POST", f"/sms/{service_name}/jobs", body)
			
			# Log du succès
			success_msg = f"SMS envoyé: {phone_number} via {sender}"
			if result.get('ids'):
				success_msg += f" - ID:{result['ids'][0]}"
			frappe.logger().info(success_msg)
			
			return {
				"success": True,
				"message": f"SMS envoyé avec succès vers {phone_number}",
				"sender_used": sender,
				"details": result
			}
			
		except Exception as e:
			error_msg = f"Erreur envoi SMS: {str(e)}"
			frappe.log_error(error_msg)
			return {
				"success": False,
				"message": error_msg
			}

	def test_connection(self):
		"""Teste la connexion à l'API OVH"""
		try:
			# Test de base
			account_info = self._make_ovh_request("GET", "/me")
			
			if not account_info:
				return {"success": False, "message": "Réponse vide de l'API OVH"}
			
			# Test des services SMS
			services = self._make_ovh_request("GET", "/sms")
			
			if not services:
				return {
					"success": False,
					"message": "Connexion API réussie mais aucun service SMS trouvé"
				}
			
			# Récupérer les détails du service
			service_name = services[0] if services else None
			service_details = None
			
			if service_name:
				try:
					service_details = self._make_ovh_request("GET", f"/sms/{service_name}")
				except:
					pass
			
			# Récupérer les expéditeurs
			available_senders = []
			if service_name:
				try:
					available_senders = self._make_ovh_request("GET", f"/sms/{service_name}/senders")
				except:
					pass
			
			# Construire le message de succès
			success_message = f"✅ Connexion réussie!\n"
			success_message += f"Compte: {account_info.get('nichandle', 'N/A')}\n"
			success_message += f"Service: {service_name or 'N/A'}\n"
			
			if service_details:
				success_message += f"Crédits: {service_details.get('creditsLeft', 'N/A')}\n"
			
			if available_senders:
				success_message += f"Expéditeurs: {', '.join(available_senders[:3])}"
				if len(available_senders) > 3:
					success_message += f" (et {len(available_senders)-3} autres)"
			else:
				success_message += "⚠️ Aucun expéditeur configuré - sera créé automatiquement"
			
			return {
				"success": True,
				"message": success_message
			}
			
		except Exception as e:
			return {
				"success": False,
				"message": f"Erreur de connexion: {str(e)}"
			}

# MÉTHODES GLOBALES POUR L'API - TOUTES LES MÉTHODES NÉCESSAIRES

@frappe.whitelist()
def test_ovh_connection():
	"""API pour tester la connexion OVH depuis l'interface"""
	try:
		settings = frappe.get_single('OVH SMS Settings')
		
		if not settings.enabled:
			return {
				"success": False,
				"message": "L'intégration OVH SMS n'est pas activée"
			}
		
		return settings.test_connection()
		
	except Exception as e:
		frappe.log_error(f"Erreur test connexion OVH: {e}")
		return {
			"success": False,
			"message": f"Erreur lors du test: {str(e)}"
		}

@frappe.whitelist()
def send_test_sms(phone_number=None, message=None):
	"""Envoie un SMS de test"""
	try:
		if not phone_number:
			return {
				"success": False,
				"message": "Numéro de téléphone requis"
			}
		
		if not message:
			message = f"Test SMS depuis ERPNext - {datetime.datetime.now().strftime('%H:%M')}"
		
		settings = frappe.get_single('OVH SMS Settings')
		
		if not settings.enabled:
			return {
				"success": False,
				"message": "L'intégration OVH SMS n'est pas activée"
			}
		
		return settings.send_sms(message, phone_number)
		
	except Exception as e:
		frappe.log_error(f"Erreur envoi SMS test: {e}")
		return {
			"success": False,
			"message": f"Erreur lors de l'envoi: {str(e)}"
		}

@frappe.whitelist()
def get_account_balance():
	"""Récupère le solde du compte SMS"""
	try:
		settings = frappe.get_single('OVH SMS Settings')
		
		if not settings.enabled:
			return {"success": False, "message": "Intégration désactivée"}
		
		service_name = settings.get_service_name()
		service_details = settings.get_service_details(service_name)
		
		return {
			"success": True,
			"credits": service_details.get('creditsLeft', 0),
			"service_name": service_name,
			"status": service_details.get('status', 'unknown')
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur récupération solde: {e}")
		return {
			"success": False,
			"message": f"Erreur: {str(e)}"
		}

@frappe.whitelist()
def get_available_senders():
	"""Récupère la liste des expéditeurs disponibles - MÉTHODE MANQUANTE AJOUTÉE"""
	try:
		settings = frappe.get_single('OVH SMS Settings')
		
		if not settings.enabled:
			return {"success": False, "message": "Intégration désactivée"}
		
		senders = settings.get_available_senders()
		
		return {
			"success": True,
			"senders": senders,
			"count": len(senders),
			"message": f"{len(senders)} expéditeur(s) trouvé(s)"
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur récupération expéditeurs: {e}")
		return {
			"success": False,
			"message": f"Erreur: {str(e)}"
		}

@frappe.whitelist()
def create_new_sender(sender_name, description="ERPNext Sender"):
	"""Crée un nouvel expéditeur SMS"""
	try:
		settings = frappe.get_single('OVH SMS Settings')
		
		if not settings.enabled:
			return {"success": False, "message": "Intégration désactivée"}
		
		return settings.create_sender(sender_name, description)
		
	except Exception as e:
		frappe.log_error(f"Erreur création expéditeur: {e}")
		return {
			"success": False,
			"message": f"Erreur: {str(e)}"
		}

@frappe.whitelist()
def test_ovh_manual(app_key, app_secret, consumer_key):
	"""Test manuel avec des clés en clair pour diagnostiquer"""
	try:
		frappe.logger().info("=== TEST MANUEL OVH ===")
		
		# Créer signature manuellement
		timestamp = str(int(time.time()))
		method = "GET"
		url = "https://eu.api.ovh.com/1.0/me"
		body = ""
		
		pre_hash = f"{app_secret}+{consumer_key}+{method}+{url}+{body}+{timestamp}"
		sha1_hash = hashlib.sha1(pre_hash.encode('utf-8')).hexdigest()
		signature = f"$1${sha1_hash}"
		
		headers = {
			"X-Ovh-Application": app_key,
			"X-Ovh-Consumer": consumer_key,
			"X-Ovh-Signature": signature,
			"X-Ovh-Timestamp": timestamp
		}
		
		response = requests.get(url, headers=headers, timeout=30)
		
		if response.status_code == 200:
			account_info = response.json()
			return {
				"success": True,
				"message": f"✅ Test manuel réussi! Compte: {account_info.get('nichandle')}"
			}
		else:
			return {
				"success": False,
				"message": f"❌ Test manuel échoué: {response.status_code} - {response.text}"
			}
		
	except Exception as e:
		return {
			"success": False,
			"message": f"Erreur test manuel: {str(e)}"
		}

def get_ovh_settings():
	"""Récupère les paramètres OVH SMS"""
	settings = frappe.get_single('OVH SMS Settings')
	
	if not settings.enabled:
		frappe.throw(_("L'intégration OVH SMS n'est pas activée"))
	
	return {
		"application_key": settings.application_key,
		"application_secret": settings.get_decrypted_password("application_secret"),
		"consumer_key": settings.get_decrypted_password("consumer_key"),
		"enabled": settings.enabled
	}

def send_sms(message, phone_number, sender=None):
	"""Fonction publique pour envoyer un SMS"""
	try:
		settings = frappe.get_single('OVH SMS Settings')
		
		if not settings.enabled:
			frappe.throw(_("L'intégration OVH SMS n'est pas activée"))
		
		return settings.send_sms(message, phone_number, sender)
		
	except Exception as e:
		frappe.log_error(f"Erreur envoi SMS public: {e}")
		frappe.throw(_("Erreur lors de l'envoi SMS: {0}").format(str(e)))
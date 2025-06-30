# Code OVH SMS Settings - Version avec UNIQUEMENT le logging corrigé

import frappe
import requests
import hashlib
import datetime
from frappe.model.document import Document
from frappe import _

class OVHSMSSettings(Document):
	def validate(self):
		if self.enabled:
			if not self.application_key:
				frappe.throw(_("Application Key est requis"))
			if not self.application_secret:
				frappe.throw(_("Application Secret est requis"))
			if not self.consumer_key:
				frappe.throw(_("Consumer Key est requis"))
			if not self.auto_detect_service and not self.service_name:
				frappe.throw(_("Service Name est requis si la détection automatique est désactivée"))

	def get_service_name(self):
		"""Récupère le nom du service SMS"""
		if not self.auto_detect_service and self.service_name:
			return self.service_name
		
		# Auto-détection
		try:
			services = self.get_sms_services()
			if services:
				return services[0]
			else:
				frappe.throw(_("Aucun service SMS trouvé sur votre compte OVH"))
		except Exception as e:
			frappe.throw(_("Erreur lors de la récupération des services SMS: {0}").format(str(e)))

	def get_sms_services(self):
		"""Récupère la liste des services SMS disponibles"""
		try:
			signature_data = self._create_signature("GET", "https://eu.api.ovh.com/1.0/sms", "")
			
			headers = {
				"X-Ovh-Application": self.application_key,
				"X-Ovh-Consumer": self.consumer_key,
				"X-Ovh-Signature": signature_data["signature"],
				"X-Ovh-Timestamp": signature_data["timestamp"]
			}
			
			response = requests.get("https://eu.api.ovh.com/1.0/sms", headers=headers, timeout=30)
			response.raise_for_status()
			
			return response.json()
		except Exception as e:
			frappe.log_error(f"Erreur récupération services SMS: {e}")
			raise

	def get_service_details(self, service_name):
		"""Récupère les détails d'un service SMS"""
		try:
			url = f"https://eu.api.ovh.com/1.0/sms/{service_name}"
			signature_data = self._create_signature("GET", url, "")
			
			headers = {
				"X-Ovh-Application": self.application_key,
				"X-Ovh-Consumer": self.consumer_key,
				"X-Ovh-Signature": signature_data["signature"],
				"X-Ovh-Timestamp": signature_data["timestamp"]
			}
			
			response = requests.get(url, headers=headers, timeout=30)
			response.raise_for_status()
			
			return response.json()
		except Exception as e:
			frappe.log_error(f"Erreur récupération détails service {service_name}: {e}")
			raise

	def get_available_senders(self):
		"""Récupère la liste des expéditeurs disponibles"""
		try:
			service_name = self.get_service_name()
			url = f"https://eu.api.ovh.com/1.0/sms/{service_name}/senders"
			signature_data = self._create_signature("GET", url, "")
			
			headers = {
				"X-Ovh-Application": self.application_key,
				"X-Ovh-Consumer": self.consumer_key,
				"X-Ovh-Signature": signature_data["signature"],
				"X-Ovh-Timestamp": signature_data["timestamp"]
			}
			
			response = requests.get(url, headers=headers, timeout=30)
			response.raise_for_status()
			
			return response.json()
		except Exception as e:
			frappe.log_error(f"Erreur récupération expéditeurs: {e}")
			return []

	def create_sender(self, sender_name, description="ERPNext Sender"):
		"""Crée un nouvel expéditeur SMS"""
		try:
			service_name = self.get_service_name()
			url = f"https://eu.api.ovh.com/1.0/sms/{service_name}/senders"
			
			# Validation du nom de l'expéditeur
			if not re.match(r'^[a-zA-Z0-9]{1,11}$', sender_name):
				raise ValueError("Le nom de l'expéditeur doit contenir uniquement des caractères alphanumériques (max 11 caractères)")
			
			body_data = {
				"sender": sender_name,
				"description": description
			}
			
			import json
			body = json.dumps(body_data, separators=(',', ':'))
			
			signature_data = self._create_signature("POST", url, body)
			
			headers = {
				"X-Ovh-Application": self.application_key,
				"X-Ovh-Consumer": self.consumer_key,
				"X-Ovh-Signature": signature_data["signature"],
				"X-Ovh-Timestamp": signature_data["timestamp"],
				"Content-Type": "application/json"
			}
			
			response = requests.post(url, data=body, headers=headers, timeout=30)
			response.raise_for_status()
			
			result = response.json()
			
			# Log de succès en tant qu'info, pas erreur - CORRECTION ICI
			frappe.logger().info(f"Expéditeur SMS créé: {sender_name}")
			
			return {
				"success": True,
				"message": f"Expéditeur '{sender_name}' créé avec succès",
				"details": result
			}
			
		except requests.exceptions.RequestException as e:
			error_msg = f"Erreur création expéditeur: {e}"
			if hasattr(e, 'response') and e.response is not None:
				try:
					error_detail = e.response.json()
					error_msg += f" - {error_detail.get('message', '')}"
				except:
					error_msg += f" - {e.response.text}"
			
			frappe.log_error(error_msg)
			return {
				"success": False,
				"message": error_msg
			}
		except Exception as e:
			error_msg = f"Erreur inattendue création expéditeur: {str(e)}"
			frappe.log_error(error_msg)
			return {
				"success": False,
				"message": error_msg
			}

	def validate_and_create_sender(self, sender):
		"""Valide un expéditeur et le crée si nécessaire"""
		try:
			available_senders = self.get_available_senders()
			
			# Si l'expéditeur existe déjà
			if sender in available_senders:
				return {
					"success": True,
					"message": f"Expéditeur '{sender}' disponible",
					"created": False
				}
			
			# Sinon, tenter de le créer
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
				# Utiliser le premier expéditeur disponible
				return available_senders[0]
			
			# Aucun expéditeur disponible, créer un expéditeur par défaut
			default_names = ["ERPNext", "ERP", "System", "SMS"]
			
			for name in default_names:
				result = self.create_sender(name)
				if result["success"]:
					return name
			
			# Si tout échoue, utiliser un nom générique
			frappe.throw(_("Impossible de créer un expéditeur SMS valide"))
			
		except Exception as e:
			frappe.log_error(f"Erreur récupération expéditeur: {e}")
			return "ERPNext"  # Fallback

	def _create_signature(self, method, url, body=""):
		"""Crée la signature OVH - VERSION ORIGINALE QUI FONCTIONNAIT"""
		timestamp = str(int(datetime.datetime.now().timestamp()))
		
		# Construction du pre-hash selon la documentation OVH
		pre_hash = f"{self.application_secret}+{self.consumer_key}+{method}+{url}+{body}+{timestamp}"
		
		# Calcul SHA1 et ajout du préfixe
		signature = "$1$" + hashlib.sha1(pre_hash.encode('utf-8')).hexdigest()
		
		return {
			"signature": signature,
			"timestamp": timestamp
		}

	def send_sms(self, message, phone_number, sender=None):
		"""Envoie un SMS via l'API OVH - UNIQUEMENT LE LOGGING CORRIGÉ"""
		try:
			service_name = self.get_service_name()
			url = f"https://eu.api.ovh.com/1.0/sms/{service_name}/jobs"
			
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
				"noStopClause": False,  # Ajouter la clause STOP pour la conformité
				"priority": "high"
			}
			
			import json
			body = json.dumps(body_data, separators=(',', ':'))
			signature_data = self._create_signature("POST", url, body)
			
			headers = {
				"X-Ovh-Application": self.application_key,
				"X-Ovh-Consumer": self.consumer_key,
				"X-Ovh-Signature": signature_data["signature"],
				"X-Ovh-Timestamp": signature_data["timestamp"],
				"Content-Type": "application/json"
			}
			
			response = requests.post(url, data=body, headers=headers, timeout=30)
			response.raise_for_status()
			
			result = response.json()
			
			# CORRECTION PRINCIPALE: Log du succès en tant qu'INFO, pas ERROR
			success_msg = f"SMS envoyé: {phone_number} via {sender}"
			if result.get('ids'):
				success_msg += f" - ID:{result['ids'][0]}"
			frappe.logger().info(success_msg)  # INFO au lieu de frappe.log_error
			
			return {
				"success": True,
				"message": f"SMS envoyé avec succès vers {phone_number}",
				"sender_used": sender,
				"details": result
			}
			
		except requests.exceptions.RequestException as e:
			error_msg = f"Erreur envoi SMS: {e}"
			if hasattr(e, 'response') and e.response is not None:
				try:
					error_detail = e.response.json()
					error_msg += f" - {error_detail.get('message', '')}"
				except:
					error_msg += f" - {e.response.text}"
			
			frappe.log_error(error_msg)
			return {
				"success": False,
				"message": error_msg
			}
		except Exception as e:
			error_msg = f"Erreur inattendue envoi SMS: {str(e)}"
			frappe.log_error(error_msg)
			return {
				"success": False,
				"message": error_msg
			}

	def test_connection(self):
		"""Teste la connexion à l'API OVH - VERSION ORIGINALE"""
		try:
			# Test de base avec /me
			signature_data = self._create_signature("GET", "https://eu.api.ovh.com/1.0/me", "")
			
			headers = {
				"X-Ovh-Application": self.application_key,
				"X-Ovh-Consumer": self.consumer_key,
				"X-Ovh-Signature": signature_data["signature"],
				"X-Ovh-Timestamp": signature_data["timestamp"]
			}
			
			response = requests.get("https://eu.api.ovh.com/1.0/me", headers=headers, timeout=30)
			response.raise_for_status()
			
			account_info = response.json()
			
			# Test des services SMS
			services = self.get_sms_services()
			
			if not services:
				return {
					"success": False,
					"message": "Connexion API réussie mais aucun service SMS trouvé"
				}
			
			# Test du service spécifique si configuré
			service_name = self.get_service_name()
			service_details = self.get_service_details(service_name)
			
			# Test des expéditeurs
			available_senders = self.get_available_senders()
			sender_info = f"Expéditeurs disponibles: {', '.join(available_senders)}" if available_senders else "Aucun expéditeur configuré"
			
			return {
				"success": True,
				"message": f"""Connexion réussie!
Compte: {account_info.get('nichandle')}
Service: {service_name}
Crédits: {service_details.get('creditsLeft', 'N/A')}
{sender_info}"""
			}
			
		except requests.exceptions.RequestException as e:
			error_msg = f"Erreur de connexion: {e}"
			if hasattr(e, 'response') and e.response is not None:
				try:
					error_detail = e.response.json()
					error_msg += f" - {error_detail.get('message', '')}"
				except:
					error_msg += f" - {e.response.text}"
			
			frappe.log_error(error_msg)
			return {
				"success": False,
				"message": error_msg
			}
		except Exception as e:
			error_msg = f"Erreur inattendue: {str(e)}"
			frappe.log_error(error_msg)
			return {
				"success": False,
				"message": error_msg
			}


# MÉTHODES GLOBALES POUR L'API - VERSION ORIGINALE

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
	"""Envoie un SMS de test - VERSION ORIGINALE"""
	try:
		# Vérification des paramètres
		if not phone_number:
			return {
				"success": False,
				"message": "Numéro de téléphone requis pour l'envoi de SMS"
			}
		
		if not message:
			message = f"Test SMS depuis ERPNext - {datetime.datetime.now().strftime('%H:%M')}"
		
		settings = frappe.get_single('OVH SMS Settings')
		
		if not settings.enabled:
			return {
				"success": False,
				"message": "L'intégration OVH SMS n'est pas activée"
			}
		
		# Envoi du SMS
		result = settings.send_sms(message, phone_number)
		
		return result
		
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
	"""Récupère la liste des expéditeurs disponibles"""
	try:
		settings = frappe.get_single('OVH SMS Settings')
		
		if not settings.enabled:
			return {"success": False, "message": "Intégration désactivée"}
		
		senders = settings.get_available_senders()
		
		return {
			"success": True,
			"senders": senders,
			"count": len(senders)
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
		
		result = settings.create_sender(sender_name, description)
		
		return result
		
	except Exception as e:
		frappe.log_error(f"Erreur création expéditeur: {e}")
		return {
			"success": False,
			"message": f"Erreur: {str(e)}"
		}

def get_ovh_settings():
	"""Récupère les paramètres OVH SMS pour les autres modules"""
	settings = frappe.get_single('OVH SMS Settings')
	
	if not settings.enabled:
		frappe.throw(_("L'intégration OVH SMS n'est pas activée"))
	
	return {
		"application_key": settings.application_key,
		"application_secret": settings.application_secret,
		"consumer_key": settings.consumer_key,
		"service_name": settings.get_service_name(),
		"enabled": settings.enabled
	}

def send_sms(message, phone_number, sender=None):
	"""Fonction publique pour envoyer un SMS depuis d'autres modules"""
	try:
		settings = frappe.get_single('OVH SMS Settings')
		
		if not settings.enabled:
			frappe.throw(_("L'intégration OVH SMS n'est pas activée"))
		
		return settings.send_sms(message, phone_number, sender)
		
	except Exception as e:
		frappe.log_error(f"Erreur envoi SMS public: {e}")
		frappe.throw(_("Erreur lors de l'envoi SMS: {0}").format(str(e)))
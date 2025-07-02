# Code OVH SMS Settings - Version avec diagnostics complets et test manuel

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
		"""Récupère et décrypte un champ de type Password avec diagnostics"""
		try:
			methods_tried = []
			
			# Méthode 1 : get_password (recommandée pour les champs Password)
			try:
				password_value = self.get_password(fieldname)
				methods_tried.append(f"get_password: {'OK' if password_value else 'VIDE'}")
				if password_value:
					return password_value.strip()
			except Exception as e:
				methods_tried.append(f"get_password: ERREUR - {str(e)}")
			
			# Méthode 2 : Récupération directe
			try:
				direct_value = self.get(fieldname)
				methods_tried.append(f"get(): {'OK' if direct_value else 'VIDE'}")
				if direct_value:
					return str(direct_value).strip()
			except Exception as e:
				methods_tried.append(f"get(): ERREUR - {str(e)}")
			
			# Méthode 3 : Récupération depuis la base de données
			try:
				if self.name:
					db_value = frappe.db.get_value(self.doctype, self.name, fieldname)
					methods_tried.append(f"db_get_value: {'OK' if db_value else 'VIDE'}")
					if db_value:
						return str(db_value).strip()
			except Exception as e:
				methods_tried.append(f"db_get_value: ERREUR - {str(e)}")
			
			# Log des tentatives
			frappe.logger().error(f"Échec récupération {fieldname}: {', '.join(methods_tried)}")
			return None
			
		except Exception as e:
			frappe.log_error(f"Erreur récupération password {fieldname}: {str(e)}")
			return None

	def _get_ovh_server_time(self):
		"""Récupère le temps synchronisé du serveur OVH"""
		try:
			response = requests.get("https://eu.api.ovh.com/1.0/auth/time", timeout=10)
			if response.status_code == 200:
				server_time = int(response.text.strip())
				local_time = int(time.time())
				drift = server_time - local_time
				frappe.logger().info(f"OVH Time - Server: {server_time}, Local: {local_time}, Drift: {drift}s")
				return server_time
		except Exception as e:
			frappe.logger().warning(f"Impossible de récupérer le temps OVH: {e}")
		
		# Fallback sur temps local
		local_time = int(time.time())
		frappe.logger().info(f"OVH Time - Using local time: {local_time}")
		return local_time

	def _create_signature_debug(self, method, url, body="", debug=True):
		"""
		Crée la signature OVH avec diagnostics très détaillés
		"""
		try:
			# Obtenir le timestamp
			timestamp = str(self._get_ovh_server_time())
			
			# Récupération des clés avec diagnostics
			app_secret = self.get_decrypted_password("application_secret")
			consumer_key = self.get_decrypted_password("consumer_key")
			
			if debug:
				frappe.logger().info("=== DIAGNOSTIC SIGNATURE OVH ===")
				frappe.logger().info(f"Method: {method}")
				frappe.logger().info(f"URL: {url}")
				frappe.logger().info(f"Body: {body[:100]}{'...' if len(body) > 100 else ''}")
				frappe.logger().info(f"Timestamp: {timestamp}")
				frappe.logger().info(f"App Key: {self.application_key[:8]}...{self.application_key[-4:] if len(self.application_key) > 12 else ''}")
				frappe.logger().info(f"App Secret: {'OK' if app_secret else 'VIDE'} ({len(app_secret) if app_secret else 0} chars)")
				frappe.logger().info(f"Consumer Key: {'OK' if consumer_key else 'VIDE'} ({len(consumer_key) if consumer_key else 0} chars)")
			
			# Vérifications
			if not app_secret:
				raise ValueError("Application Secret vide ou non récupéré")
			if not consumer_key:
				raise ValueError("Consumer Key vide ou non récupéré")
			
			# Construire la chaîne de hachage selon la doc OVH EXACTE
			# Format: APPLICATION_SECRET+CONSUMER_KEY+METHOD+URL+BODY+TIMESTAMP
			pre_hash = f"{app_secret}+{consumer_key}+{method}+{url}+{body}+{timestamp}"
			
			if debug:
				frappe.logger().info(f"Pre-hash: {pre_hash[:50]}...{pre_hash[-20:] if len(pre_hash) > 70 else pre_hash}")
				frappe.logger().info(f"Pre-hash length: {len(pre_hash)}")
			
			# Calculer le hash SHA1
			sha1_hash = hashlib.sha1(pre_hash.encode('utf-8')).hexdigest()
			
			# Ajouter le préfixe $1$
			signature = f"$1${sha1_hash}"
			
			if debug:
				frappe.logger().info(f"SHA1 Hash: {sha1_hash}")
				frappe.logger().info(f"Final Signature: {signature}")
				frappe.logger().info("=== FIN DIAGNOSTIC ===")
			
			return {
				"signature": signature,
				"timestamp": timestamp,
				"pre_hash_length": len(pre_hash),
				"app_secret_length": len(app_secret),
				"consumer_key_length": len(consumer_key)
			}
			
		except Exception as e:
			frappe.log_error(f"Erreur création signature OVH: {str(e)}")
			raise

	def _make_ovh_request_debug(self, method, endpoint, body="", debug=True):
		"""Effectue une requête OVH avec diagnostics complets"""
		url = f"https://eu.api.ovh.com/1.0{endpoint}"
		
		try:
			signature_data = self._create_signature_debug(method, url, body, debug)
			
			consumer_key = self.get_decrypted_password("consumer_key")
			if not consumer_key:
				raise ValueError("Consumer Key non récupéré")
			
			headers = {
				"X-Ovh-Application": str(self.application_key).strip(),
				"X-Ovh-Consumer": consumer_key,
				"X-Ovh-Signature": signature_data["signature"],
				"X-Ovh-Timestamp": signature_data["timestamp"]
			}
			
			if method.upper() in ["POST", "PUT"]:
				headers["Content-Type"] = "application/json"
			
			if debug:
				frappe.logger().info("=== HEADERS ENVOYÉS ===")
				for key, value in headers.items():
					if key in ["X-Ovh-Consumer", "X-Ovh-Signature"]:
						frappe.logger().info(f"{key}: {value[:10]}...{value[-4:]}")
					else:
						frappe.logger().info(f"{key}: {value}")
			
			# Effectuer la requête
			if method.upper() == "GET":
				response = requests.get(url, headers=headers, timeout=30)
			elif method.upper() == "POST":
				response = requests.post(url, data=body, headers=headers, timeout=30)
			else:
				raise ValueError(f"Méthode HTTP non supportée: {method}")
			
			if debug:
				frappe.logger().info(f"Response Status: {response.status_code}")
				frappe.logger().info(f"Response Headers: {dict(response.headers)}")
			
			response.raise_for_status()
			return response.json()
			
		except requests.exceptions.HTTPError as e:
			error_response = ""
			try:
				error_response = e.response.text
			except:
				pass
			
			error_msg = f"Erreur HTTP {e.response.status_code}: {e.response.reason}"
			
			if debug:
				frappe.logger().error(f"=== ERREUR HTTP ===")
				frappe.logger().error(f"Status: {e.response.status_code}")
				frappe.logger().error(f"Response: {error_response}")
				frappe.logger().error(f"Request URL: {url}")
				frappe.logger().error(f"Request Method: {method}")
			
			# Diagnostic spécifique pour les erreurs de signature
			if e.response.status_code == 400:
				error_msg += f" - Réponse: {error_response}"
				
				# Ajouter des suggestions
				if "Invalid signature" in error_response:
					error_msg += " | SUGGESTIONS: 1) Vérifiez les clés OVH, 2) Vérifiez les permissions du Consumer Key, 3) Regénérez le Consumer Key"
				elif "Invalid timestamp" in error_response:
					error_msg += " | SUGGESTIONS: Problème de synchronisation temps"
				elif "Invalid application" in error_response:
					error_msg += " | SUGGESTIONS: Application Key incorrecte"
			
			frappe.log_error(error_msg)
			raise Exception(error_msg)
			
		except Exception as e:
			frappe.log_error(f"Erreur requête OVH: {str(e)}")
			raise

	def test_connection_debug(self):
		"""Test de connexion avec diagnostics complets"""
		try:
			frappe.logger().info("=== DÉBUT TEST CONNEXION OVH ===")
			
			# Vérifications préliminaires
			if not self.application_key or len(self.application_key.strip()) == 0:
				return {"success": False, "message": "Application Key manquant"}
			
			app_secret = self.get_decrypted_password("application_secret")
			if not app_secret:
				return {"success": False, "message": "Application Secret manquant ou non récupéré"}
			
			consumer_key = self.get_decrypted_password("consumer_key")
			if not consumer_key:
				return {"success": False, "message": "Consumer Key manquant ou non récupéré"}
			
			# Diagnostic des clés
			frappe.logger().info(f"=== DIAGNOSTIC CLÉS ===")
			frappe.logger().info(f"App Key: {len(self.application_key)} chars - {self.application_key[:8]}...")
			frappe.logger().info(f"App Secret: {len(app_secret)} chars")
			frappe.logger().info(f"Consumer Key: {len(consumer_key)} chars")
			
			# Test de connexion basique avec debug
			frappe.logger().info("=== TEST CONNEXION /me ===")
			account_info = self._make_ovh_request_debug("GET", "/me", "", debug=True)
			
			if not account_info:
				return {"success": False, "message": "Réponse vide de l'API OVH"}
			
			frappe.logger().info(f"=== CONNEXION RÉUSSIE ===")
			frappe.logger().info(f"Compte OVH: {account_info.get('nichandle')}")
			
			# Test des services SMS
			frappe.logger().info("=== TEST SERVICES SMS ===")
			services = self._make_ovh_request_debug("GET", "/sms", "", debug=False)
			
			success_message = f"✅ Connexion réussie!\n"
			success_message += f"Compte: {account_info.get('nichandle', 'N/A')}\n"
			success_message += f"Services SMS: {len(services) if services else 0}\n"
			
			if services:
				success_message += f"Premier service: {services[0]}"
			else:
				success_message += "⚠️ Aucun service SMS trouvé"
			
			return {
				"success": True,
				"message": success_message
			}
			
		except Exception as e:
			frappe.logger().error(f"=== ÉCHEC TEST CONNEXION ===")
			frappe.logger().error(f"Erreur: {str(e)}")
			return {
				"success": False,
				"message": f"Erreur de connexion: {str(e)}"
			}

	# Méthodes simplifiées pour le fonctionnement normal
	def get_service_name(self):
		try:
			if not self.auto_detect_service and self.service_name:
				return self.service_name
			
			services = self._make_ovh_request_debug("GET", "/sms", "", debug=False)
			if services:
				return services[0]
			else:
				frappe.throw(_("Aucun service SMS trouvé"))
		except Exception as e:
			frappe.throw(_("Erreur services SMS: {0}").format(str(e)))

	def send_sms(self, message, phone_number, sender=None):
		try:
			service_name = self.get_service_name()
			
			if not sender:
				sender = "ERPNext"  # Fallback simple
			
			body_data = {
				"message": message,
				"receivers": [phone_number],
				"sender": sender,
				"noStopClause": False,
				"priority": "high"
			}
			
			body = json.dumps(body_data, separators=(',', ':'))
			result = self._make_ovh_request_debug("POST", f"/sms/{service_name}/jobs", body, debug=False)
			
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

# MÉTHODES GLOBALES POUR L'API

@frappe.whitelist()
def test_ovh_connection():
	"""Test de connexion avec diagnostics complets"""
	try:
		settings = frappe.get_single('OVH SMS Settings')
		
		if not settings.enabled:
			return {
				"success": False,
				"message": "L'intégration OVH SMS n'est pas activée"
			}
		
		return settings.test_connection_debug()
		
	except Exception as e:
		frappe.log_error(f"Erreur test connexion OVH: {e}")
		return {
			"success": False,
			"message": f"Erreur lors du test: {str(e)}"
		}

@frappe.whitelist()
def test_ovh_manual(app_key, app_secret, consumer_key):
	"""Test manuel avec des clés en clair pour diagnostiquer"""
	try:
		frappe.logger().info("=== TEST MANUEL OVH ===")
		frappe.logger().info(f"App Key: {len(app_key)} chars")
		frappe.logger().info(f"App Secret: {len(app_secret)} chars")
		frappe.logger().info(f"Consumer Key: {len(consumer_key)} chars")
		
		# Créer signature manuellement
		timestamp = str(int(time.time()))
		method = "GET"
		url = "https://eu.api.ovh.com/1.0/me"
		body = ""
		
		pre_hash = f"{app_secret}+{consumer_key}+{method}+{url}+{body}+{timestamp}"
		sha1_hash = hashlib.sha1(pre_hash.encode('utf-8')).hexdigest()
		signature = f"$1${sha1_hash}"
		
		frappe.logger().info(f"Signature: {signature}")
		
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
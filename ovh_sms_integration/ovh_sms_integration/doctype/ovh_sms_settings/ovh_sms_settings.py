# Remplacez le contenu de ovh_sms_settings.py - Version avec correction Password

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
			if not self.get_application_secret():
				frappe.throw(_("Application Secret est requis"))
			if not self.get_consumer_key():
				frappe.throw(_("Consumer Key est requis"))
			if not self.auto_detect_service and not self.service_name:
				frappe.throw(_("Service Name est requis si la détection automatique est désactivée"))

	def get_application_secret(self):
		"""Récupère l'Application Secret (même si c'est un champ Password)"""
		# Si le champ est masqué par des étoiles, récupérer depuis la base
		if self.application_secret and self.application_secret.startswith('*'):
			return frappe.get_password("OVH SMS Settings", "OVH SMS Settings", "application_secret")
		return self.application_secret

	def get_consumer_key(self):
		"""Récupère le Consumer Key (même si c'est un champ Password)"""
		# Si le champ est masqué par des étoiles, récupérer depuis la base
		if self.consumer_key and self.consumer_key.startswith('*'):
			return frappe.get_password("OVH SMS Settings", "OVH SMS Settings", "consumer_key")
		return self.consumer_key

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
				"X-Ovh-Consumer": self.get_consumer_key(),
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
				"X-Ovh-Consumer": self.get_consumer_key(),
				"X-Ovh-Signature": signature_data["signature"],
				"X-Ovh-Timestamp": signature_data["timestamp"]
			}
			
			response = requests.get(url, headers=headers, timeout=30)
			response.raise_for_status()
			
			return response.json()
		except Exception as e:
			frappe.log_error(f"Erreur récupération détails service {service_name}: {e}")
			raise

	def _create_signature(self, method, url, body=""):
		"""Crée la signature OVH"""
		timestamp = str(int(datetime.datetime.now().timestamp()))
		
		# Récupération sécurisée des clés
		app_secret = self.get_application_secret()
		consumer_key = self.get_consumer_key()
		
		# Construction du pre-hash selon la documentation OVH
		pre_hash = f"{app_secret}+{consumer_key}+{method}+{url}+{body}+{timestamp}"
		
		# Calcul SHA1 et ajout du préfixe
		signature = "$1$" + hashlib.sha1(pre_hash.encode('utf-8')).hexdigest()
		
		return {
			"signature": signature,
			"timestamp": timestamp
		}

	def test_connection(self):
		"""Teste la connexion à l'API OVH"""
		try:
			# Vérification que les clés sont récupérables
			app_secret = self.get_application_secret()
			consumer_key = self.get_consumer_key()
			
			if not app_secret or not consumer_key:
				return {
					"success": False,
					"message": "Impossible de récupérer les clés API. Vérifiez la configuration."
				}
			
			# Test de base avec /me
			signature_data = self._create_signature("GET", "https://eu.api.ovh.com/1.0/me", "")
			
			headers = {
				"X-Ovh-Application": self.application_key,
				"X-Ovh-Consumer": consumer_key,
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
			
			return {
				"success": True,
				"message": f"Connexion réussie! Compte: {account_info.get('nichandle')}, Service: {service_name}, Crédits: {service_details.get('creditsLeft', 'N/A')}"
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

# MÉTHODES GLOBALES POUR L'API

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
def send_test_sms(phone_number, message="Test SMS depuis ERPNext"):
	"""Envoie un SMS de test"""
	try:
		settings = frappe.get_single('OVH SMS Settings')
		
		if not settings.enabled:
			frappe.throw(_("L'intégration OVH SMS n'est pas activée"))
		
		# Import de la fonction d'envoi
		from ovh_sms_integration.utils.sms_utils import send_sms
		
		result = send_sms(message, phone_number)
		
		return {
			"success": True,
			"message": f"SMS de test envoyé avec succès vers {phone_number}",
			"details": result
		}
		
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

def get_ovh_settings():
	"""Récupère les paramètres OVH SMS pour les autres modules"""
	settings = frappe.get_single('OVH SMS Settings')
	
	if not settings.enabled:
		frappe.throw(_("L'intégration OVH SMS n'est pas activée"))
	
	return {
		"application_key": settings.application_key,
		"application_secret": settings.get_application_secret(),
		"consumer_key": settings.get_consumer_key(),
		"service_name": settings.get_service_name(),
		"enabled": settings.enabled
	}
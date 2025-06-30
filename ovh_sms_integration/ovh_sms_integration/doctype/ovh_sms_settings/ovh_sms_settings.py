# -*- coding: utf-8 -*-
"""
OVH SMS Settings - Version avec logging corrigé
Gère correctement les logs de succès et d'erreur avec respect des limites de caractères
"""

import frappe
import requests
import hashlib
import datetime
import json
import re
from frappe.model.document import Document
from frappe import _


def log_sms_activity(level, message, details=None):
	"""
	Fonction de logging optimisée pour les SMS
	Respecte la limite de 140 caractères et évite les logs en cascade
	"""
	try:
		# Tronquer le message si trop long
		if len(message) > 130:
			message = message[:127] + "..."
		
		# Pour les succès, utiliser les logs normaux plutôt que frappe.log_error
		if level == "success":
			frappe.logger().info(f"SMS: {message}")
			if details:
				frappe.logger().debug(f"SMS Details: {str(details)[:200]}")
		elif level == "error":
			frappe.log_error(message, "OVH SMS Error")
			if details:
				frappe.logger().error(f"SMS Error Details: {str(details)[:200]}")
		elif level == "warning":
			frappe.logger().warning(f"SMS: {message}")
		else:
			frappe.logger().info(f"SMS: {message}")
			
	except Exception as e:
		# Éviter les logs en cascade en cas d'erreur de logging
		pass


class OVHSMSSettings(Document):
	def validate(self):
		"""Validation des paramètres OVH SMS"""
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
			log_sms_activity("error", f"Erreur récupération services SMS: {str(e)[:80]}")
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
			log_sms_activity("error", f"Erreur détails service {service_name}: {str(e)[:60]}")
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
			log_sms_activity("error", f"Erreur récupération expéditeurs: {str(e)[:70]}")
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
			log_sms_activity("success", f"Expéditeur {sender_name} créé avec succès")
			
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
			
			log_sms_activity("error", error_msg[:120])
			return {
				"success": False,
				"message": error_msg
			}
		except Exception as e:
			error_msg = f"Erreur inattendue création expéditeur: {str(e)}"
			log_sms_activity("error", error_msg[:100])
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
			log_sms_activity("error", f"Erreur récupération expéditeur: {str(e)[:80]}")
			return "ERPNext"  # Fallback

	def _create_signature(self, method, url, body=""):
		"""Crée la signature OVH"""
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
		"""Envoie un SMS via l'API OVH - VERSION AVEC LOGGING CORRIGÉ"""
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
					log_sms_activity("warning", f"Expéditeur {sender} indisponible, fallback automatique")
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
			
			# Log de succès optimisé
			log_sms_activity("success", 
				f"SMS envoyé: {phone_number} via {sender} - ID:{result.get('ids', [''])[0]}")
			
			# Mise à jour des statistiques
			self._update_sms_stats(result.get('totalCreditsRemoved', 1))
			
			return {
				"success": True,
				"message": f"SMS envoyé avec succès vers {phone_number}",
				"sender_used": sender,
				"sms_id": result.get('ids', [''])[0],
				"credits_used": result.get('totalCreditsRemoved', 1)
			}
			
		except requests.exceptions.RequestException as e:
			error_msg = f"Erreur envoi SMS: {str(e)[:80]}"
			if hasattr(e, 'response') and e.response is not None:
				try:
					error_detail = e.response.json()
					error_msg = f"API Error: {error_detail.get('message', str(e))[:100]}"
				except:
					error_msg = f"HTTP {e.response.status_code}: {str(e)[:80]}"
			
			log_sms_activity("error", error_msg)
			return {
				"success": False,
				"message": error_msg
			}
		except Exception as e:
			error_msg = f"Erreur inattendue SMS: {str(e)[:80]}"
			log_sms_activity("error", error_msg)
			return {
				"success": False,
				"message": error_msg
			}

	def _update_sms_stats(self, credits_used=1):
		"""Met à jour les statistiques d'utilisation SMS"""
		try:
			# Mise à jour des compteurs
			self.total_sms_sent = (self.total_sms_sent or 0) + 1
			self.total_credits_used = (self.total_credits_used or 0) + credits_used
			self.last_sms_sent = datetime.datetime.now()
			
			# Calcul SMS envoyés aujourd'hui
			today = datetime.date.today()
			if hasattr(self, 'last_stats_update') and self.last_stats_update:
				if self.last_stats_update.date() == today:
					self.sms_sent_today = (self.sms_sent_today or 0) + 1
				else:
					self.sms_sent_today = 1
			else:
				self.sms_sent_today = 1
			
			# Calcul moyenne par jour
			if self.total_sms_sent > 0:
				days_since_install = max(1, (datetime.date.today() - datetime.date(2024, 1, 1)).days)
				self.average_sms_per_day = round(self.total_sms_sent / days_since_install, 2)
			
			# Sauvegarde sans validation pour éviter les conflits
			self.db_set('total_sms_sent', self.total_sms_sent, commit=True)
			self.db_set('total_credits_used', self.total_credits_used, commit=True)
			self.db_set('sms_sent_today', self.sms_sent_today, commit=True)
			self.db_set('last_sms_sent', self.last_sms_sent, commit=True)
			self.db_set('average_sms_per_day', self.average_sms_per_day, commit=True)
			
		except Exception as e:
			# Ignorer les erreurs de mise à jour des stats pour ne pas bloquer l'envoi
			log_sms_activity("warning", f"Erreur mise à jour stats: {str(e)[:60]}")

	def test_connection(self):
		"""Teste la connexion à l'API OVH"""
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
			
			# Test du service spécifique
			service_name = self.get_service_name()
			service_details = self.get_service_details(service_name)
			
			# Test des expéditeurs
			available_senders = self.get_available_senders()
			sender_info = f"Expéditeurs: {', '.join(available_senders[:3])}" if available_senders else "Aucun expéditeur"
			
			log_sms_activity("success", f"Test connexion OVH réussi - {account_info.get('nichandle')}")
			
			return {
				"success": True,
				"message": f"""Connexion réussie!
Compte: {account_info.get('nichandle')}
Service: {service_name}
Crédits: {service_details.get('creditsLeft', 'N/A')}
{sender_info}"""
			}
			
		except requests.exceptions.RequestException as e:
			error_msg = f"Erreur de connexion: {str(e)[:80]}"
			if hasattr(e, 'response') and e.response is not None:
				try:
					error_detail = e.response.json()
					error_msg = f"API Error: {error_detail.get('message', str(e))[:100]}"
				except:
					error_msg = f"HTTP {e.response.status_code}: {str(e)[:80]}"
			
			log_sms_activity("error", error_msg)
			return {
				"success": False,
				"message": error_msg
			}
		except Exception as e:
			error_msg = f"Erreur inattendue test: {str(e)[:80]}"
			log_sms_activity("error", error_msg)
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
		log_sms_activity("error", f"Erreur test connexion: {str(e)[:80]}")
		return {
			"success": False,
			"message": f"Erreur lors du test: {str(e)[:100]}"
		}

@frappe.whitelist()
def send_test_sms(phone_number=None, message=None):
	"""Envoie un SMS de test - VERSION AVEC LOGGING CORRIGÉ"""
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
		
		# Mise à jour du résultat du test dans les paramètres
		if result["success"]:
			test_result = f"✅ SMS envoyé avec succès vers {phone_number} à {datetime.datetime.now().strftime('%H:%M:%S')}"
			settings.db_set('last_test_result', test_result, commit=True)
		else:
			test_result = f"❌ Erreur: {result['message']} à {datetime.datetime.now().strftime('%H:%M:%S')}"
			settings.db_set('last_test_result', test_result, commit=True)
		
		return result
		
	except Exception as e:
		error_msg = f"Erreur envoi SMS test: {str(e)[:80]}"
		log_sms_activity("error", error_msg)
		return {
			"success": False,
			"message": error_msg
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
		
		# Mise à jour du solde dans les paramètres
		balance = service_details.get('creditsLeft', 0)
		settings.db_set('sms_balance', balance, commit=True)
		settings.db_set('last_balance_check', datetime.datetime.now(), commit=True)
		
		return {
			"success": True,
			"credits": balance,
			"service_name": service_name,
			"status": service_details.get('status', 'unknown')
		}
		
	except Exception as e:
		log_sms_activity("error", f"Erreur récupération solde: {str(e)[:70]}")
		return {
			"success": False,
			"message": f"Erreur: {str(e)[:100]}"
		}

@frappe.whitelist()
def get_available_senders():
	"""Récupère la liste des expéditeurs disponibles"""
	try:
		settings = frappe.get_single('OVH SMS Settings')
		
		if not settings.enabled:
			return {"success": False, "message": "Intégration désactivée"}
		
		senders = settings.get_available_senders()
		
		# Mise à jour de la liste dans les paramètres
		senders_text = ", ".join(senders) if senders else "Aucun expéditeur configuré"
		settings.db_set('available_senders', senders_text, commit=True)
		
		return {
			"success": True,
			"senders": senders,
			"count": len(senders)
		}
		
	except Exception as e:
		log_sms_activity("error", f"Erreur récupération expéditeurs: {str(e)[:60]}")
		return {
			"success": False,
			"message": f"Erreur: {str(e)[:100]}"
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
		log_sms_activity("error", f"Erreur création expéditeur: {str(e)[:60]}")
		return {
			"success": False,
			"message": f"Erreur: {str(e)[:100]}"
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
		log_sms_activity("error", f"Erreur envoi SMS public: {str(e)[:70]}")
		frappe.throw(_("Erreur lors de l'envoi SMS: {0}").format(str(e)[:100]))
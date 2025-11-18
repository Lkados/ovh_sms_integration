# -*- coding: utf-8 -*-
"""OVH SMS Settings doctype.

Ce module gère la configuration et les interactions avec l'API OVH SMS.
Il fournit les fonctionnalités de:
- Configuration des credentials OVH
- Envoi de SMS via l'API OVH
- Gestion des expéditeurs (senders)
- Récupération du solde SMS
- Test de connexion
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import TYPE_CHECKING, Any

import frappe
import requests
from frappe import _
from frappe.model.document import Document

if TYPE_CHECKING:
	from ovh_sms_integration.types import SMSResult


class OVHSMSSettings(Document):
	"""DocType de configuration pour l'intégration OVH SMS.

	Gère tous les paramètres nécessaires pour se connecter à l'API OVH
	et envoyer des SMS.

	Attributes:
		enabled (bool): Active/désactive l'intégration
		application_key (str): Clé d'application OVH
		application_secret (Password): Secret d'application OVH
		consumer_key (Password): Clé consommateur OVH
		auto_detect_service (bool): Active la détection automatique du service SMS
		service_name (str): Nom du service SMS (si auto-detect désactivé)
		default_sender (str): Expéditeur par défaut pour les SMS
	"""

	def validate(self) -> None:
		"""Valide la configuration avant sauvegarde.

		Raises:
			frappe.ValidationError: Si des champs requis sont manquants.

		Note:
			- Vérifie les credentials OVH si l'intégration est activée
			- Valide que service_name est fourni si auto-detect est désactivé
		"""
		if self.enabled:
			if not self.application_key:
				frappe.throw(_("Application Key est requis"))
			if not self.get_password("application_secret"):
				frappe.throw(_("Application Secret est requis"))
			if not self.get_password("consumer_key"):
				frappe.throw(_("Consumer Key est requis"))
			if not self.auto_detect_service and not self.service_name:
				frappe.throw(_("Service Name est requis si la détection automatique est désactivée"))

	def get_service_name(self) -> str:
		"""Récupère le nom du service SMS OVH.

		Retourne le service_name configuré ou détecte automatiquement
		le premier service SMS disponible sur le compte OVH.

		Returns:
			str: Nom du service SMS (ex: "sms-ab123456-1").

		Raises:
			frappe.ValidationError: Si aucun service SMS n'est trouvé
				ou si l'API retourne une erreur.

		Example:
			>>> settings = frappe.get_doc("OVH SMS Settings")
			>>> service = settings.get_service_name()
			>>> print(service)
			sms-ab123456-1

		Note:
			- Si auto_detect_service=False, retourne self.service_name
			- Sinon, appelle l'API pour lister les services et retourne le premier
		"""
		if not self.auto_detect_service and self.service_name:
			return self.service_name

		# Auto-détection
		try:
			services = self.get_sms_services()
			if services:
				return services[0]
			frappe.throw(_("Aucun service SMS trouvé sur votre compte OVH"))
			return ""  # unreachable, but for mypy
		except Exception as e:
			frappe.throw(_("Erreur lors de la récupération des services SMS: {0}").format(str(e)))
			return ""  # unreachable, but for mypy

	def get_sms_services(self) -> list[str]:
		"""Récupère la liste des services SMS disponibles sur le compte OVH.

		Appelle l'API OVH pour lister tous les services SMS actifs.

		Returns:
			list[str]: Liste des noms de services SMS (ex: ["sms-ab123456-1", "sms-cd789012-2"]).

		Raises:
			Exception: Si l'appel API échoue.

		Example:
			>>> settings = frappe.get_doc("OVH SMS Settings")
			>>> services = settings.get_sms_services()
			>>> print(services)
			['sms-ab123456-1']

		Note:
			- Utilise la signature OVH pour l'authentification
			- Les erreurs sont loggées avant d'être propagées
		"""
		try:
			signature_data = self._create_signature("GET", "https://eu.api.ovh.com/1.0/sms", "")

			headers = {
				"X-Ovh-Application": self.application_key,
				"X-Ovh-Consumer": self.get_password("consumer_key"),
				"X-Ovh-Signature": signature_data["signature"],
				"X-Ovh-Timestamp": signature_data["timestamp"],
			}

			response = requests.get("https://eu.api.ovh.com/1.0/sms", headers=headers, timeout=30)
			response.raise_for_status()

			return response.json()
		except Exception as e:
			frappe.log_error(f"Erreur récupération services SMS: {e}")
			raise

	def get_service_details(self, service_name: str) -> dict[str, Any]:
		"""Récupère les détails d'un service SMS OVH.

		Args:
			service_name: Nom du service SMS (ex: "sms-ab123456-1").

		Returns:
			dict: Détails du service avec les champs:
				- creditsLeft (float): Crédits SMS restants
				- status (str): Statut du service
				- name (str): Nom du service
				- autres champs OVH

		Raises:
			Exception: Si l'appel API échoue.

		Example:
			>>> settings = frappe.get_doc("OVH SMS Settings")
			>>> details = settings.get_service_details("sms-ab123456-1")
			>>> print(f"Crédits: {details['creditsLeft']}")

		Note:
			Les erreurs sont loggées avant d'être propagées.
		"""
		try:
			url = f"https://eu.api.ovh.com/1.0/sms/{service_name}"
			signature_data = self._create_signature("GET", url, "")

			headers = {
				"X-Ovh-Application": self.application_key,
				"X-Ovh-Consumer": self.get_password("consumer_key"),
				"X-Ovh-Signature": signature_data["signature"],
				"X-Ovh-Timestamp": signature_data["timestamp"],
			}

			response = requests.get(url, headers=headers, timeout=30)
			response.raise_for_status()

			return response.json()
		except Exception as e:
			frappe.log_error(f"Erreur récupération détails service {service_name}: {e}")
			raise

	def get_available_senders(self) -> list[str]:
		"""Récupère la liste des expéditeurs SMS disponibles.

		Retourne tous les expéditeurs (senders) validés et disponibles
		pour l'envoi de SMS sur ce service OVH.

		Returns:
			list[str]: Liste des noms d'expéditeurs (ex: ["ERPNext", "MyCompany"]).
				Retourne [] en cas d'erreur.

		Example:
			>>> settings = frappe.get_doc("OVH SMS Settings")
			>>> senders = settings.get_available_senders()
			>>> print(senders)
			['ERPNext', 'MyApp']

		Note:
			- Les erreurs sont loggées mais ne lèvent pas d'exception
			- Retourne une liste vide si l'API échoue
			- Les expéditeurs doivent être validés par OVH avant utilisation
		"""
		try:
			service_name = self.get_service_name()
			url = f"https://eu.api.ovh.com/1.0/sms/{service_name}/senders"
			signature_data = self._create_signature("GET", url, "")

			headers = {
				"X-Ovh-Application": self.application_key,
				"X-Ovh-Consumer": self.get_password("consumer_key"),
				"X-Ovh-Signature": signature_data["signature"],
				"X-Ovh-Timestamp": signature_data["timestamp"],
			}

			response = requests.get(url, headers=headers, timeout=30)
			response.raise_for_status()

			return response.json()
		except Exception as e:
			frappe.log_error(f"Erreur récupération expéditeurs: {e}")
			return []

	def create_sender(self, sender_name: str, description: str = "ERPNext Sender") -> "SMSResult":
		"""Crée un nouvel expéditeur SMS sur le compte OVH.

		Soumet une demande de création d'expéditeur à OVH. L'expéditeur
		doit être validé par OVH avant utilisation (peut prendre quelques heures).

		Args:
			sender_name: Nom de l'expéditeur (1-11 caractères alphanum uniquement).
			description: Description de l'expéditeur (pour référence interne).
				Par défaut "ERPNext Sender".

		Returns:
			SMSResult: Résultat de la création avec:
				- success (bool): True si création réussie
				- message (str): Message de statut
				- details (dict): Détails de la réponse OVH

		Example:
			>>> settings = frappe.get_doc("OVH SMS Settings")
			>>> result = settings.create_sender("MyCompany", "Sender for marketing")
			>>> if result["success"]:
			...     print("Expéditeur créé, en attente de validation OVH")

		Raises:
			ValueError: Si sender_name ne respecte pas le format (alphanumerique, 1-11 chars).

		Note:
			- Format requis: [a-zA-Z0-9]{1,11}
			- L'expéditeur nécessite une validation manuelle par OVH
			- Les SMS avec expéditeur non validé échoueront
		"""
		try:
			service_name = self.get_service_name()
			url = f"https://eu.api.ovh.com/1.0/sms/{service_name}/senders"

			# Validation du nom de l'expéditeur
			if not re.match(r"^[a-zA-Z0-9]{1,11}$", sender_name):
				raise ValueError(
					"Le nom de l'expéditeur doit contenir uniquement des caractères alphanum ériques (max 11 caractères)"
				)

			import json

			body_data = {"sender": sender_name, "description": description}

			body = json.dumps(body_data, separators=(",", ":"))

			signature_data = self._create_signature("POST", url, body)

			headers = {
				"X-Ovh-Application": self.application_key,
				"X-Ovh-Consumer": self.get_password("consumer_key"),
				"X-Ovh-Signature": signature_data["signature"],
				"X-Ovh-Timestamp": signature_data["timestamp"],
				"Content-Type": "application/json",
			}

			response = requests.post(url, data=body, headers=headers, timeout=30)
			response.raise_for_status()

			result = response.json()

			# Log de succès en INFO, pas ERROR
			frappe.logger().info(f"Expéditeur SMS créé: {sender_name}")

			return {"success": True, "message": f"Expéditeur '{sender_name}' créé avec succès", "details": result}

		except requests.exceptions.RequestException as e:
			error_msg = f"Erreur création expéditeur: {e}"
			if hasattr(e, "response") and e.response is not None:
				try:
					error_detail = e.response.json()
					error_msg += f" - {error_detail.get('message', '')}"
				except:
					error_msg += f" - {e.response.text}"

			frappe.log_error(error_msg)
			return {"success": False, "message": error_msg}
		except Exception as e:
			error_msg = f"Erreur inattendue création expéditeur: {str(e)}"
			frappe.log_error(error_msg)
			return {"success": False, "message": error_msg}

	def validate_and_create_sender(self, sender: str) -> dict[str, Any]:
		"""Valide qu'un expéditeur existe ou le crée si nécessaire.

		Vérifie si l'expéditeur est dans la liste des expéditeurs disponibles.
		Si absent, tente de le créer automatiquement.

		Args:
			sender: Nom de l'expéditeur à valider/créer.

		Returns:
			dict: Résultat avec:
				- success (bool): True si expéditeur disponible ou créé
				- message (str): Message de statut
				- created (bool): True si créé, False si déjà existant

		Example:
			>>> settings = frappe.get_doc("OVH SMS Settings")
			>>> result = settings.validate_and_create_sender("MyApp")
			>>> if result["success"] and result["created"]:
			...     print("Nouvel expéditeur créé")

		Note:
			Les erreurs ne lèvent pas d'exception, mais retournent success=False.
		"""
		try:
			available_senders = self.get_available_senders()

			# Si l'expéditeur existe déjà
			if sender in available_senders:
				return {"success": True, "message": f"Expéditeur '{sender}' disponible", "created": False}

			# Sinon, tenter de le créer
			result = self.create_sender(sender)
			if result["success"]:
				return {**result, "created": True}

			return {**result, "created": False}

		except Exception as e:
			return {"success": False, "message": f"Erreur validation expéditeur: {str(e)}", "created": False}

	def get_best_sender(self) -> str:
		"""Retourne le meilleur expéditeur disponible ou en crée un.

		Stratégie de sélection d'expéditeur par ordre de priorité:
		1. default_sender configuré (si existe ou peut être créé)
		2. Premier expéditeur disponible dans la liste OVH
		3. Création automatique d'un expéditeur ("ERPNext", "ERP", "System", "SMS")
		4. Fallback vers "ERPNext" si tout échoue

		Returns:
			str: Nom de l'expéditeur à utiliser.

		Example:
			>>> settings = frappe.get_doc("OVH SMS Settings")
			>>> sender = settings.get_best_sender()
			>>> print(f"Utilisation de l'expéditeur: {sender}")

		Raises:
			frappe.ValidationError: Si impossible de créer un expéditeur valide.

		Note:
			- Essaie automatiquement plusieurs noms en cas d'échec
			- Les erreurs sont loggées
			- Retourne toujours une valeur (fallback "ERPNext")
		"""
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
				result: SMSResult = self.create_sender(name)
				if result["success"]:
					return name

			# Si tout échoue, utiliser un nom générique
			frappe.throw(_("Impossible de créer un expéditeur SMS valide"))
			return "ERPNext"  # unreachable, but for mypy

		except Exception as e:
			frappe.log_error(f"Erreur récupération expéditeur: {e}")
			return "ERPNext"  # Fallback

	def _create_signature(self, method: str, url: str, body: str = "") -> dict[str, str]:
		"""Crée la signature OVH pour l'authentification API.

		Génère la signature SHA1 requise par l'API OVH selon leur documentation.
		Format: $1$ + SHA1(app_secret+consumer_key+method+url+body+timestamp)

		Args:
			method: Méthode HTTP ("GET", "POST", "PUT", "DELETE").
			url: URL complète de l'endpoint API.
			body: Corps de la requête (vide pour GET).
				Par défaut "".

		Returns:
			dict[str, str]: Dictionnaire avec:
				- signature (str): Signature SHA1 avec préfixe $1$
				- timestamp (str): Timestamp Unix utilisé

		Example:
			>>> settings = frappe.get_doc("OVH SMS Settings")
			>>> sig = settings._create_signature("GET", "https://eu.api.ovh.com/1.0/sms", "")
			>>> print(sig["signature"])
			$1$a1b2c3d4e5f6...

		Note:
			- Utilise get_password() pour récupérer les credentials chiffrés
			- Le timestamp est généré automatiquement
			- La signature est valide quelques minutes seulement
		"""
		timestamp = str(int(datetime.now().timestamp()))

		# Utiliser get_password() pour les champs Password
		app_secret = self.get_password("application_secret") or self.application_secret
		consumer_key = self.get_password("consumer_key") or self.consumer_key

		# Construction du pre-hash selon la documentation OVH
		pre_hash = f"{app_secret}+{consumer_key}+{method}+{url}+{body}+{timestamp}"

		# Calcul SHA1 et ajout du préfixe
		signature = "$1$" + hashlib.sha1(pre_hash.encode("utf-8")).hexdigest()

		return {"signature": signature, "timestamp": timestamp}

	def send_sms(self, message: str, phone_number: str, sender: str | None = None) -> "SMSResult":
		"""Envoie un SMS via l'API OVH.

		Méthode principale d'envoi de SMS. Gère automatiquement:
		- La sélection de l'expéditeur (sender)
		- L'authentification API
		- La conformité (clause STOP)

		Args:
			message: Contenu du SMS à envoyer.
			phone_number: Numéro du destinataire (format international).
			sender: Expéditeur optionnel. Si None, utilise get_best_sender().

		Returns:
			SMSResult: Résultat de l'envoi avec:
				- success (bool): True si envoi réussi
				- message (str): Message de statut
				- sender_used (str): Expéditeur effectivement utilisé
				- details (dict): Réponse complète de l'API OVH

		Example:
			>>> settings = frappe.get_doc("OVH SMS Settings")
			>>> result = settings.send_sms(
			...     "Votre commande est prête",
			...     "+33612345678",
			...     "MyCompany"
			... )
			>>> if result["success"]:
			...     print(f"SMS envoyé via {result['sender_used']}")

		Note:
			- Ajoute automatiquement la clause STOP pour conformité légale
			- Priorité "high" par défaut
			- Les erreurs sont loggées mais ne lèvent pas d'exception
			- Timeout de 30 secondes
		"""
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
			import json

			body_data = {
				"message": message,
				"receivers": [phone_number],
				"sender": sender,
				"noStopClause": False,  # Ajouter la clause STOP pour la conformité
				"priority": "high",
			}

			body = json.dumps(body_data, separators=(",", ":"))
			signature_data = self._create_signature("POST", url, body)

			headers = {
				"X-Ovh-Application": self.application_key,
				"X-Ovh-Consumer": self.get_password("consumer_key"),
				"X-Ovh-Signature": signature_data["signature"],
				"X-Ovh-Timestamp": signature_data["timestamp"],
				"Content-Type": "application/json",
			}

			response = requests.post(url, data=body, headers=headers, timeout=30)
			response.raise_for_status()

			result = response.json()

			# Log du succès
			success_msg = f"SMS envoyé: {phone_number} via {sender}"
			if result.get("ids"):
				success_msg += f" - ID:{result['ids'][0]}"
			frappe.logger().info(success_msg)

			return {
				"success": True,
				"message": f"SMS envoyé avec succès vers {phone_number}",
				"sender_used": sender,
				"details": result,
			}

		except requests.exceptions.RequestException as e:
			error_msg = f"Erreur envoi SMS: {e}"
			if hasattr(e, "response") and e.response is not None:
				try:
					error_detail = e.response.json()
					error_msg += f" - {error_detail.get('message', '')}"
				except:
					error_msg += f" - {e.response.text}"

			frappe.log_error(error_msg)
			return {"success": False, "message": error_msg}
		except Exception as e:
			error_msg = f"Erreur inattendue envoi SMS: {str(e)}"
			frappe.log_error(error_msg)
			return {"success": False, "message": error_msg}

	def test_connection(self) -> dict[str, Any]:
		"""Teste la connexion à l'API OVH et vérifie la configuration.

		Effectue une série de tests pour valider:
		- Connexion API avec credentials
		- Accès aux informations de compte
		- Disponibilité des services SMS
		- Détails du service configuré
		- Expéditeurs disponibles

		Returns:
			dict[str, Any]: Résultat du test avec:
				- success (bool): True si tous les tests passent
				- message (str): Message détaillé avec infos compte/service

		Example:
			>>> settings = frappe.get_doc("OVH SMS Settings")
			>>> result = settings.test_connection()
			>>> if result["success"]:
			...     print(result["message"])

		Note:
			- Teste d'abord l'endpoint /me pour vérifier les credentials
			- Vérifie ensuite la disponibilité des services SMS
			- Récupère les détails du service et les expéditeurs
			- Les erreurs sont loggées mais ne lèvent pas d'exception
		"""
		try:
			# Test de base avec /me
			signature_data = self._create_signature("GET", "https://eu.api.ovh.com/1.0/me", "")
			
			headers = {
				"X-Ovh-Application": self.application_key,
				"X-Ovh-Consumer": self.get_password("consumer_key"),  # CORRECTION ICI
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


# MÉTHODES GLOBALES POUR L'API

@frappe.whitelist()
def test_ovh_connection() -> dict[str, Any]:
	"""API endpoint pour tester la connexion OVH depuis l'interface.

	Fonction whitelistée accessible via l'API Frappe pour tester
	la configuration OVH depuis le frontend.

	Returns:
		dict[str, Any]: Résultat du test avec:
			- success (bool): État du test
			- message (str): Message de statut ou d'erreur

	Raises:
		frappe.ValidationError: Si l'intégration n'est pas activée.

	Note:
		- Accessible via frappe.call() depuis JavaScript
		- Délègue le test à settings.test_connection()
		- Les erreurs sont loggées automatiquement
	"""
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
def send_test_sms(phone_number: str | None = None, message: str | None = None) -> dict[str, Any]:
	"""API endpoint pour envoyer un SMS de test depuis l'interface.

	Fonction whitelistée pour tester l'envoi de SMS avec un numéro
	et un message personnalisés.

	Args:
		phone_number: Numéro de téléphone destinataire (format international).
			Par défaut None.
		message: Contenu du SMS. Si None, génère un message avec timestamp.
			Par défaut None.

	Returns:
		dict[str, Any]: Résultat de l'envoi (voir SMSResult).

	Example:
		>>> # Depuis JavaScript
		>>> frappe.call({
		...     method: "ovh_sms_integration...send_test_sms",
		...     args: {
		...         phone_number: "+33612345678",
		...         message: "Test SMS"
		...     }
		... })

	Note:
		- Génère automatiquement un message si non fourni
		- Format: "Test SMS depuis ERPNext - HH:MM"
		- Vérifie que l'intégration est activée
	"""
	try:
		# Vérification des paramètres
		if not phone_number:
			return {
				"success": False,
				"message": "Numéro de téléphone requis pour l'envoi de SMS"
			}
		
		if not message:
			message = f"Test SMS depuis ERPNext - {datetime.now().strftime('%H:%M')}"
		
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
def get_account_balance() -> dict[str, Any]:
	"""API endpoint pour récupérer le solde du compte SMS.

	Fonction whitelistée pour obtenir le nombre de crédits SMS
	restants depuis l'interface.

	Returns:
		dict[str, Any]: Informations sur le solde avec:
			- success (bool): État de la requête
			- credits (float): Nombre de crédits restants
			- service_name (str): Nom du service SMS
			- status (str): État du service
			- message (str): Message d'erreur si échec

	Example:
		>>> # Depuis JavaScript
		>>> frappe.call({
		...     method: "ovh_sms_integration...get_account_balance",
		...     callback: function(r) {
		...         console.log("Crédits:", r.message.credits);
		...     }
		... })

	Note:
		- Nécessite que l'intégration soit activée
		- Récupère les crédits depuis les détails du service OVH
	"""
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
def get_available_senders() -> dict[str, Any]:
	"""API endpoint pour récupérer la liste des expéditeurs disponibles.

	Fonction whitelistée pour obtenir tous les expéditeurs validés
	pour le service SMS depuis l'interface.

	Returns:
		dict[str, Any]: Liste des expéditeurs avec:
			- success (bool): État de la requête
			- senders (list[str]): Liste des noms d'expéditeurs
			- count (int): Nombre d'expéditeurs
			- message (str): Message d'erreur si échec

	Example:
		>>> # Depuis JavaScript
		>>> frappe.call({
		...     method: "ovh_sms_integration...get_available_senders",
		...     callback: function(r) {
		...         console.log("Expéditeurs:", r.message.senders);
		...     }
		... })

	Note:
		- Nécessite que l'intégration soit activée
		- Retourne uniquement les expéditeurs validés par OVH
	"""
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
def create_new_sender(sender_name: str, description: str = "ERPNext Sender") -> "SMSResult":
	"""API endpoint pour créer un nouvel expéditeur SMS.

	Fonction whitelistée pour créer et soumettre un nouvel expéditeur
	pour validation par OVH depuis l'interface.

	Args:
		sender_name: Nom de l'expéditeur (max 11 caractères alphanumériques).
		description: Description de l'expéditeur pour la validation OVH.
			Par défaut "ERPNext Sender".

	Returns:
		SMSResult: Résultat de la création avec:
			- success (bool): État de la création
			- message (str): Confirmation ou erreur
			- details (dict): Détails de la réponse OVH

	Example:
		>>> # Depuis JavaScript
		>>> frappe.call({
		...     method: "ovh_sms_integration...create_new_sender",
		...     args: {
		...         sender_name: "MyCompany",
		...         description: "Société de services"
		...     }
		... })

	Note:
		- L'expéditeur nécessite une validation par OVH
		- Peut prendre plusieurs jours selon le type d'expéditeur
		- Maximum 11 caractères pour les noms alphanumériques
	"""
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

def get_ovh_settings() -> dict[str, Any]:
	"""Récupère les paramètres OVH SMS pour les autres modules.

	Fonction interne pour obtenir la configuration complète OVH
	depuis d'autres modules de l'application.

	Returns:
		dict[str, Any]: Configuration OVH avec:
			- application_key (str): Clé d'application
			- application_secret (str): Secret d'application (décrypté)
			- consumer_key (str): Clé consommateur (décryptée)
			- service_name (str): Nom du service SMS
			- enabled (bool): État de l'intégration

	Raises:
		frappe.ValidationError: Si l'intégration n'est pas activée.

	Example:
		>>> # Depuis sms_utils.py
		>>> config = get_ovh_settings()
		>>> app_key = config["application_key"]

	Note:
		- Utilise get_password() pour décrypter les secrets
		- Fallback sur les valeurs en clair si get_password() échoue
		- Lève une exception si intégration désactivée
	"""
	settings = frappe.get_single('OVH SMS Settings')

	if not settings.enabled:
		frappe.throw(_("L'intégration OVH SMS n'est pas activée"))

	return {
		"application_key": settings.application_key,
		"application_secret": settings.get_password("application_secret") or settings.application_secret,
		"consumer_key": settings.get_password("consumer_key") or settings.consumer_key,
		"service_name": settings.get_service_name(),
		"enabled": settings.enabled
	}

def send_sms(message: str, phone_number: str, sender: str | None = None) -> "SMSResult":
	"""Fonction publique pour envoyer un SMS depuis d'autres modules.

	Point d'entrée principal pour l'envoi de SMS depuis n'importe quel
	module de l'application (sms_utils, tasks, etc.).

	Args:
		message: Contenu du SMS à envoyer.
		phone_number: Numéro du destinataire (format international).
		sender: Expéditeur optionnel. Si None, utilise le défaut.
			Par défaut None.

	Returns:
		SMSResult: Résultat de l'envoi (voir SMSResult TypedDict).

	Raises:
		frappe.ValidationError: Si l'intégration n'est pas activée.
		frappe.ValidationError: En cas d'erreur lors de l'envoi.

	Example:
		>>> # Depuis sms_utils.py
		>>> from ovh_sms_integration...ovh_sms_settings import send_sms
		>>> result = send_sms(
		...     "Votre commande est prête",
		...     "+33612345678"
		... )

	Note:
		- Délègue à settings.send_sms() pour l'envoi réel
		- Les erreurs sont loggées et relancées
		- Vérifie automatiquement que l'intégration est activée
	"""
	try:
		settings = frappe.get_single('OVH SMS Settings')

		if not settings.enabled:
			frappe.throw(_("L'intégration OVH SMS n'est pas activée"))

		return settings.send_sms(message, phone_number, sender)

	except Exception as e:
		frappe.log_error(f"Erreur envoi SMS public: {e}")
		frappe.throw(_("Erreur lors de l'envoi SMS: {0}").format(str(e)))
		# unreachable, but for mypy
		return {"success": False, "message": str(e), "sender_used": None, "details": None, "sent": 0, "failed": 1}
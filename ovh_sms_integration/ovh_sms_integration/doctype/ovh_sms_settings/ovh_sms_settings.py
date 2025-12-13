# -*- coding: utf-8 -*-
"""OVH SMS Settings doctype.

Ce module gère la configuration et les interactions avec l'API OVH SMS.
"""
from __future__ import annotations

import hashlib
import json
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

    Attributes:
        enabled (bool): Active/désactive l'intégration
        application_key (str): Clé d'application OVH
        application_secret (Password): Secret d'application OVH
        consumer_key (Password): Clé consommateur OVH
        auto_detect_service (bool): Détection automatique du service SMS
        service_name (str): Nom du service SMS
        default_sender (str): Expéditeur par défaut
    """

    def validate(self) -> None:
        """Valide la configuration avant sauvegarde."""
        if self.enabled:
            if not self.application_key:
                frappe.throw(_("Application Key est requis"))
            if not self.get_password("application_secret"):
                frappe.throw(_("Application Secret est requis"))
            if not self.get_password("consumer_key"):
                frappe.throw(_("Consumer Key est requis"))
            if not self.auto_detect_service and not self.service_name:
                frappe.throw(
                    _(
                        "Service Name est requis si la détection automatique "
                        "est désactivée"
                    )
                )

    def get_service_name(self) -> str:
        """Récupère le nom du service SMS OVH.

        Returns:
            str: Nom du service SMS.
        """
        if not self.auto_detect_service and self.service_name:
            return self.service_name

        try:
            services = self.get_sms_services()
            if services:
                return services[0]
            frappe.throw(_("Aucun service SMS trouvé sur votre compte OVH"))
            return ""
        except Exception as e:
            frappe.throw(
                _("Erreur lors de la récupération des services SMS: {0}").format(str(e))
            )
            return ""

    def get_sms_services(self) -> list[str]:
        """Récupère la liste des services SMS disponibles.

        Returns:
            list[str]: Liste des noms de services SMS.
        """
        try:
            signature_data = self._create_signature(
                "GET", "https://eu.api.ovh.com/1.0/sms", ""
            )

            headers = {
                "X-Ovh-Application": self.application_key,
                "X-Ovh-Consumer": self.get_password("consumer_key"),
                "X-Ovh-Signature": signature_data["signature"],
                "X-Ovh-Timestamp": signature_data["timestamp"],
            }

            response = requests.get(
                "https://eu.api.ovh.com/1.0/sms", headers=headers, timeout=30
            )
            response.raise_for_status()

            return response.json()
        except Exception as e:
            frappe.log_error(f"Erreur récupération services SMS: {e}")
            raise

    def get_service_details(self, service_name: str) -> dict[str, Any]:
        """Récupère les détails d'un service SMS OVH.

        Args:
            service_name: Nom du service SMS.

        Returns:
            dict: Détails du service.
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
            frappe.log_error(
                f"Erreur récupération détails service {service_name}: {e}"
            )
            raise

    def get_available_senders(self) -> list[str]:
        """Récupère la liste des expéditeurs SMS disponibles.

        Returns:
            list[str]: Liste des noms d'expéditeurs.
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

    def create_sender(
        self, sender_name: str, description: str = "ERPNext Sender"
    ) -> "SMSResult":
        """Crée un nouvel expéditeur SMS sur le compte OVH.

        Args:
            sender_name: Nom de l'expéditeur (1-11 caractères alphanumériques).
            description: Description de l'expéditeur.

        Returns:
            SMSResult: Résultat de la création.
        """
        try:
            service_name = self.get_service_name()
            url = f"https://eu.api.ovh.com/1.0/sms/{service_name}/senders"

            if not re.match(r"^[a-zA-Z0-9]{1,11}$", sender_name):
                raise ValueError(
                    "Le nom de l'expéditeur doit contenir uniquement des "
                    "caractères alphanumériques (max 11 caractères)"
                )

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
            frappe.logger().info(f"Expéditeur SMS créé: {sender_name}")

            return {
                "success": True,
                "message": _("Expéditeur '{0}' créé avec succès").format(sender_name),
                "details": result,
            }

        except requests.exceptions.RequestException as e:
            error_msg = self._format_request_error(e, "création expéditeur")
            return {"success": False, "message": error_msg}
        except Exception as e:
            error_msg = f"Erreur inattendue création expéditeur: {str(e)}"
            frappe.log_error(error_msg)
            return {"success": False, "message": error_msg}

    def validate_and_create_sender(self, sender: str) -> dict[str, Any]:
        """Valide qu'un expéditeur existe ou le crée si nécessaire.

        Args:
            sender: Nom de l'expéditeur à valider/créer.

        Returns:
            dict: Résultat avec success, message, created.
        """
        try:
            available_senders = self.get_available_senders()

            if sender in available_senders:
                return {
                    "success": True,
                    "message": _("Expéditeur '{0}' disponible").format(sender),
                    "created": False,
                }

            result = self.create_sender(sender)
            if result["success"]:
                return {**result, "created": True}

            return {**result, "created": False}

        except Exception as e:
            return {
                "success": False,
                "message": _("Erreur validation expéditeur: {0}").format(str(e)),
                "created": False,
            }

    def get_best_sender(self) -> str:
        """Retourne le meilleur expéditeur disponible.

        Returns:
            str: Nom de l'expéditeur à utiliser.
        """
        try:
            if self.default_sender:
                result = self.validate_and_create_sender(self.default_sender)
                if result["success"]:
                    return self.default_sender

            available_senders = self.get_available_senders()

            if available_senders:
                return available_senders[0]

            default_names = ["ERPNext", "ERP", "System", "SMS"]

            for name in default_names:
                result = self.create_sender(name)
                if result["success"]:
                    return name

            frappe.throw(_("Impossible de créer un expéditeur SMS valide"))
            return "ERPNext"

        except Exception as e:
            frappe.log_error(f"Erreur récupération expéditeur: {e}")
            return "ERPNext"

    def _create_signature(
        self, method: str, url: str, body: str = ""
    ) -> dict[str, str]:
        """Crée la signature OVH pour l'authentification API.

        Args:
            method: Méthode HTTP.
            url: URL complète de l'endpoint API.
            body: Corps de la requête.

        Returns:
            dict[str, str]: Signature et timestamp.
        """
        timestamp = str(int(datetime.now().timestamp()))

        app_secret = self.get_password("application_secret") or self.application_secret
        consumer_key = self.get_password("consumer_key") or self.consumer_key

        pre_hash = f"{app_secret}+{consumer_key}+{method}+{url}+{body}+{timestamp}"
        signature = "$1$" + hashlib.sha1(pre_hash.encode("utf-8")).hexdigest()

        return {"signature": signature, "timestamp": timestamp}

    def _format_request_error(self, e: Exception, context: str) -> str:
        """Formate les erreurs de requêtes HTTP.

        Args:
            e: Exception de la requête.
            context: Contexte de l'erreur.

        Returns:
            str: Message d'erreur formaté.
        """
        error_msg = f"Erreur {context}: {e}"
        if hasattr(e, "response") and e.response is not None:
            try:
                error_detail = e.response.json()
                error_msg += f" - {error_detail.get('message', '')}"
            except Exception:
                error_msg += f" - {e.response.text}"

        frappe.log_error(error_msg)
        return error_msg

    def send_sms(
        self, message: str, phone_number: str, sender: str | None = None
    ) -> "SMSResult":
        """Envoie un SMS via l'API OVH.

        Args:
            message: Contenu du SMS à envoyer.
            phone_number: Numéro du destinataire.
            sender: Expéditeur optionnel.

        Returns:
            SMSResult: Résultat de l'envoi.
        """
        try:
            service_name = self.get_service_name()
            url = f"https://eu.api.ovh.com/1.0/sms/{service_name}/jobs"

            if not sender:
                sender = self.get_best_sender()
            else:
                result = self.validate_and_create_sender(sender)
                if not result["success"]:
                    frappe.logger().warning(
                        f"Impossible d'utiliser l'expéditeur {sender}, "
                        "fallback automatique"
                    )
                    sender = self.get_best_sender()

            body_data = {
                "message": message,
                "receivers": [phone_number],
                "sender": sender,
                "noStopClause": False,
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

            success_msg = f"SMS envoyé: {phone_number} via {sender}"
            if result.get("ids"):
                success_msg += f" - ID:{result['ids'][0]}"
            frappe.logger().info(success_msg)

            return {
                "success": True,
                "message": _("SMS envoyé avec succès vers {0}").format(phone_number),
                "sender_used": sender,
                "details": result,
            }

        except requests.exceptions.RequestException as e:
            error_msg = self._format_request_error(e, "envoi SMS")
            return {"success": False, "message": error_msg}
        except Exception as e:
            error_msg = f"Erreur inattendue envoi SMS: {str(e)}"
            frappe.log_error(error_msg)
            return {"success": False, "message": error_msg}

    def test_connection(self) -> dict[str, Any]:
        """Teste la connexion à l'API OVH et vérifie la configuration.

        Returns:
            dict[str, Any]: Résultat du test avec success et message.
        """
        try:
            signature_data = self._create_signature(
                "GET", "https://eu.api.ovh.com/1.0/me", ""
            )

            headers = {
                "X-Ovh-Application": self.application_key,
                "X-Ovh-Consumer": self.get_password("consumer_key"),
                "X-Ovh-Signature": signature_data["signature"],
                "X-Ovh-Timestamp": signature_data["timestamp"],
            }

            response = requests.get(
                "https://eu.api.ovh.com/1.0/me", headers=headers, timeout=30
            )
            response.raise_for_status()

            account_info = response.json()
            services = self.get_sms_services()

            if not services:
                return {
                    "success": False,
                    "message": _(
                        "Connexion API réussie mais aucun service SMS trouvé"
                    ),
                }

            service_name = self.get_service_name()
            service_details = self.get_service_details(service_name)
            available_senders = self.get_available_senders()

            sender_info = (
                _("Expéditeurs disponibles: {0}").format(", ".join(available_senders))
                if available_senders
                else _("Aucun expéditeur configuré")
            )

            message = (
                _("Connexion réussie!")
                + "\n"
                + _("Compte: {0}").format(account_info.get("nichandle"))
                + "\n"
                + _("Service: {0}").format(service_name)
                + "\n"
                + _("Crédits: {0}").format(service_details.get("creditsLeft", "N/A"))
                + "\n"
                + sender_info
            )
            return {"success": True, "message": message}

        except requests.exceptions.RequestException as e:
            error_msg = self._format_request_error(e, "connexion")
            return {"success": False, "message": error_msg}
        except Exception as e:
            error_msg = f"Erreur inattendue: {str(e)}"
            frappe.log_error(error_msg)
            return {"success": False, "message": error_msg}

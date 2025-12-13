# -*- coding: utf-8 -*-
"""OVH API helper functions and endpoints.

Ce module contient les fonctions d'API whitelistées pour OVH SMS Settings.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

import frappe
from frappe import _

if TYPE_CHECKING:
    from ovh_sms_integration.types import SMSResult


@frappe.whitelist()
def test_ovh_connection() -> dict[str, Any]:
    """API endpoint pour tester la connexion OVH depuis l'interface.

    Returns:
        dict[str, Any]: Résultat du test avec success et message.
    """
    try:
        settings = frappe.get_single("OVH SMS Settings")

        if not settings.enabled:
            return {
                "success": False,
                "message": _("L'intégration OVH SMS n'est pas activée"),
            }

        return settings.test_connection()

    except Exception as e:
        frappe.log_error(f"Erreur test connexion OVH: {e}")
        return {
            "success": False,
            "message": _("Erreur lors du test: {0}").format(str(e)),
        }


@frappe.whitelist()
def send_test_sms(
    phone_number: str | None = None, message: str | None = None
) -> dict[str, Any]:
    """API endpoint pour envoyer un SMS de test.

    Args:
        phone_number: Numéro de téléphone destinataire.
        message: Contenu du SMS.

    Returns:
        dict[str, Any]: Résultat de l'envoi.
    """
    try:
        if not phone_number:
            return {
                "success": False,
                "message": _("Numéro de téléphone requis pour l'envoi de SMS"),
            }

        if not message:
            message = f"Test SMS depuis ERPNext - {datetime.now().strftime('%H:%M')}"

        settings = frappe.get_single("OVH SMS Settings")

        if not settings.enabled:
            return {
                "success": False,
                "message": _("L'intégration OVH SMS n'est pas activée"),
            }

        return settings.send_sms(message, phone_number)

    except Exception as e:
        frappe.log_error(f"Erreur envoi SMS test: {e}")
        return {
            "success": False,
            "message": _("Erreur lors de l'envoi: {0}").format(str(e)),
        }


@frappe.whitelist()
def get_account_balance() -> dict[str, Any]:
    """API endpoint pour récupérer le solde du compte SMS.

    Returns:
        dict[str, Any]: Informations sur le solde.
    """
    try:
        settings = frappe.get_single("OVH SMS Settings")

        if not settings.enabled:
            return {"success": False, "message": _("Intégration désactivée")}

        service_name = settings.get_service_name()
        service_details = settings.get_service_details(service_name)

        return {
            "success": True,
            "credits": service_details.get("creditsLeft", 0),
            "service_name": service_name,
            "status": service_details.get("status", "unknown"),
        }

    except Exception as e:
        frappe.log_error(f"Erreur récupération solde: {e}")
        return {"success": False, "message": _("Erreur: {0}").format(str(e))}


@frappe.whitelist()
def get_available_senders() -> dict[str, Any]:
    """API endpoint pour récupérer la liste des expéditeurs disponibles.

    Returns:
        dict[str, Any]: Liste des expéditeurs.
    """
    try:
        settings = frappe.get_single("OVH SMS Settings")

        if not settings.enabled:
            return {"success": False, "message": _("Intégration désactivée")}

        senders = settings.get_available_senders()

        return {"success": True, "senders": senders, "count": len(senders)}

    except Exception as e:
        frappe.log_error(f"Erreur récupération expéditeurs: {e}")
        return {"success": False, "message": _("Erreur: {0}").format(str(e))}


@frappe.whitelist()
def create_new_sender(
    sender_name: str, description: str = "ERPNext Sender"
) -> "SMSResult":
    """API endpoint pour créer un nouvel expéditeur SMS.

    Args:
        sender_name: Nom de l'expéditeur (max 11 caractères alphanumériques).
        description: Description de l'expéditeur.

    Returns:
        SMSResult: Résultat de la création.
    """
    try:
        settings = frappe.get_single("OVH SMS Settings")

        if not settings.enabled:
            return {"success": False, "message": _("Intégration désactivée")}

        return settings.create_sender(sender_name, description)

    except Exception as e:
        frappe.log_error(f"Erreur création expéditeur: {e}")
        return {"success": False, "message": _("Erreur: {0}").format(str(e))}


def get_ovh_settings() -> dict[str, Any]:
    """Récupère les paramètres OVH SMS pour les autres modules.

    Returns:
        dict[str, Any]: Configuration OVH.
    """
    settings = frappe.get_single("OVH SMS Settings")

    if not settings.enabled:
        frappe.throw(_("L'intégration OVH SMS n'est pas activée"))

    return {
        "application_key": settings.application_key,
        "application_secret": settings.get_password("application_secret")
        or settings.application_secret,
        "consumer_key": settings.get_password("consumer_key") or settings.consumer_key,
        "service_name": settings.get_service_name(),
        "enabled": settings.enabled,
    }


def send_sms(
    message: str, phone_number: str, sender: str | None = None
) -> "SMSResult":
    """Fonction publique pour envoyer un SMS depuis d'autres modules.

    Args:
        message: Contenu du SMS à envoyer.
        phone_number: Numéro du destinataire.
        sender: Expéditeur optionnel.

    Returns:
        SMSResult: Résultat de l'envoi.
    """
    try:
        settings = frappe.get_single("OVH SMS Settings")

        if not settings.enabled:
            frappe.throw(_("L'intégration OVH SMS n'est pas activée"))

        return settings.send_sms(message, phone_number, sender)

    except Exception as e:
        frappe.log_error(f"Erreur envoi SMS public: {e}")
        frappe.throw(_("Erreur lors de l'envoi SMS: {0}").format(str(e)))
        return {"success": False, "message": str(e)}

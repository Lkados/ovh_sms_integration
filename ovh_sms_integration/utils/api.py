# -*- coding: utf-8 -*-
"""API endpoints for OVH SMS Integration.

Ce module contient les fonctions whitelistées accessibles via l'API Frappe.
"""
from __future__ import annotations

from typing import Any

import frappe
from frappe import _


@frappe.whitelist()
def get_pending_events() -> dict[str, Any]:
    """Récupère les événements en attente de rappel SMS.

    Returns:
        dict: Événements avec their détails.

    Note:
        Accessible via frappe.call() depuis JavaScript.
    """
    from ovh_sms_integration.utils.events import get_events_requiring_reminders

    try:
        events = get_events_requiring_reminders()
        return {"success": True, "events": events, "count": len(events)}
    except Exception as e:
        frappe.log_error(f"Erreur récupération événements: {e}")
        return {"success": False, "message": str(e), "events": []}


@frappe.whitelist()
def manual_send_event_reminder(
    event_name: str, test_mode: bool = False
) -> dict[str, Any]:
    """Envoie manuellement un rappel pour un événement spécifique.

    Args:
        event_name: Nom de l'événement.
        test_mode: Si True, simule l'envoi sans consommer de crédits.

    Returns:
        dict: Résultat de l'envoi avec détails par participant.
    """
    from ovh_sms_integration.utils.events import send_event_reminder_sms

    try:
        result = send_event_reminder_sms(event_name, test_mode=test_mode)
        return result
    except Exception as e:
        frappe.log_error(f"Erreur envoi rappel manuel: {e}")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def test_ovh_connection() -> dict[str, Any]:
    """Teste la connexion à l'API OVH.

    Returns:
        dict: Résultat du test avec success et message.
    """
    from ovh_sms_integration.utils.core import get_ovh_sms_settings

    settings = get_ovh_sms_settings()
    if not settings:
        return {"success": False, "message": _("OVH SMS non activé")}

    try:
        result = settings.test_connection()
        return result
    except Exception as e:
        frappe.log_error(f"Erreur test connexion OVH: {e}")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def send_manual_sms(
    phone_number: str, message: str, sender: str | None = None
) -> dict[str, Any]:
    """Envoie un SMS manuellement depuis l'interface.

    Args:
        phone_number: Numéro du destinataire.
        message: Contenu du SMS.
        sender: Expéditeur (optionnel).

    Returns:
        dict: Résultat de l'envoi.
    """
    from ovh_sms_integration.utils.core import send_sms

    if not phone_number:
        return {"success": False, "message": _("Numéro de téléphone requis")}

    if not message:
        return {"success": False, "message": _("Message requis")}

    result = send_sms(message, phone_number, sender)
    return result if result else {"success": False, "message": _("Échec de l'envoi")}


@frappe.whitelist()
def get_sms_balance() -> dict[str, Any] | None:
    """Récupère le solde de crédits SMS OVH.

    Returns:
        dict: Informations sur le solde avec credits_remaining.
    """
    from ovh_sms_integration.utils.core import get_ovh_sms_settings

    settings = get_ovh_sms_settings()
    if not settings:
        return {"success": False, "message": _("OVH SMS non activé")}

    try:
        service_name = settings.get_service_name()
        details = settings.get_service_details(service_name)
        return {
            "success": True,
            "credits_remaining": details.get("creditsLeft", 0),
            "service_name": service_name,
        }
    except Exception as e:
        frappe.log_error(f"Erreur récupération solde: {e}")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def send_test_reminder() -> dict[str, Any]:
    """API endpoint pour envoyer un rappel de test.

    Fonction whitelistée pour tester l'envoi de rappels SMS avec
    un événement et des numéros de test configurés.

    Returns:
        dict[str, Any]: Résultat du test avec:
            - success (bool): État global du test
            - message (str): Message de synthèse
            - details (list): Détails par destinataire testé

    Note:
        - Nécessite test_event, test_customer_mobile ou test_employee_mobile
        - Met à jour last_test_result dans le document
        - Teste les templates customer et employee séparément
    """
    try:
        settings = frappe.get_single("SMS Event Reminder")

        if not settings.enabled:
            return {
                "success": False,
                "message": _("Les rappels d'événements ne sont pas activés"),
            }

        if not settings.test_event:
            return {
                "success": False,
                "message": _("Aucun événement de test sélectionné"),
            }

        # Récupération de l'événement de test
        event = frappe.get_doc("Event", settings.test_event)

        results = []

        # Test client
        if settings.test_customer_mobile:
            template = settings.get_message_template("customer")
            message = settings.format_message(
                template, event, customer_name="Client Test"
            )

            result = settings.send_sms_reminder(message, settings.test_customer_mobile)
            results.append(
                {
                    "recipient": "Client",
                    "mobile": settings.test_customer_mobile,
                    "message": message,
                    "result": result,
                }
            )

        # Test employé
        if settings.test_employee_mobile:
            template = settings.get_message_template("employee")
            message = settings.format_message(
                template, event, employee_name="Employé Test"
            )

            result = settings.send_sms_reminder(message, settings.test_employee_mobile)
            results.append(
                {
                    "recipient": "Employé",
                    "mobile": settings.test_employee_mobile,
                    "message": message,
                    "result": result,
                }
            )

        if not results:
            return {"success": False, "message": _("Aucun numéro de test configuré")}

        # Mise à jour du résultat du test
        result_text = "\n".join(
            [
                f"{r['recipient']} ({r['mobile']}): "
                f"{'✓' if r['result'].get('success') else '✗'} - "
                f"{r['result'].get('message', '')}"
                for r in results
            ]
        )

        settings.db_set("last_test_result", result_text)

        success_count = sum(1 for r in results if r["result"].get("success"))

        return {
            "success": success_count > 0,
            "message": _("{0}/{1} rappels de test envoyés avec succès").format(
                success_count, len(results)
            ),
            "details": results,
        }

    except Exception as e:
        frappe.log_error(f"Erreur envoi rappel de test: {e}")
        return {"success": False, "message": _("Erreur: {0}").format(str(e))}


@frappe.whitelist()
def get_reminder_statistics() -> dict[str, Any] | None:
    """API endpoint pour récupérer les statistiques des rappels.

    Fonction whitelistée pour obtenir les statistiques d'envoi
    de rappels depuis l'interface.

    Returns:
        dict[str, Any] | None: Statistiques avec:
            - enabled (bool): État de l'intégration
            - total_sent (int): Total rappels envoyés
            - sent_today (int): Rappels envoyés aujourd'hui
            - failed_count (int): Nombre d'échecs
            - last_sent (datetime): Dernier envoi réussi
            - last_check (datetime): Dernière vérification
            - next_check (datetime): Prochaine vérification planifiée
            Retourne None en cas d'erreur.
    """
    try:
        settings = frappe.get_single("SMS Event Reminder")

        return {
            "enabled": settings.enabled,
            "total_sent": settings.total_reminders_sent or 0,
            "sent_today": settings.reminders_sent_today or 0,
            "failed_count": settings.failed_reminders_count or 0,
            "last_sent": settings.last_reminder_sent,
            "last_check": settings.last_check_time,
            "next_check": settings.next_check_time,
        }

    except Exception as e:
        frappe.log_error(f"Erreur récupération statistiques: {e}")
        return None

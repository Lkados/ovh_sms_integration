# -*- coding: utf-8 -*-
"""Event reminder utilities for OVH SMS Integration.

Ce module gère les rappels SMS pour les événements.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import frappe
from frappe import _

if TYPE_CHECKING:
    from ovh_sms_integration.types import EventParticipant, SMSResult


def get_events_requiring_reminders() -> list[dict[str, Any]]:
    """Récupère les événements nécessitant un rappel SMS.

    Returns:
        list: Liste des événements avec leurs détails.
    """
    reminder_settings = frappe.get_single("SMS Event Reminder")

    if not reminder_settings.enabled:
        return []

    hours_before = reminder_settings.hours_before or 24
    target_time = datetime.now() + timedelta(hours=hours_before)
    window_start = target_time - timedelta(minutes=30)
    window_end = target_time + timedelta(minutes=30)

    filters = {
        "starts_on": ["between", [window_start, window_end]],
        "docstatus": 1,
    }

    if reminder_settings.event_type_filter:
        filters["subject"] = ["like", f"%{reminder_settings.event_type_filter}%"]

    events = frappe.get_all(
        "Event",
        filters=filters,
        fields=["name", "subject", "starts_on", "description"],
        order_by="starts_on asc",
    )

    return events


def get_event_participants_with_mobile(event_name: str) -> list["EventParticipant"]:
    """Récupère les participants d'un événement avec leur mobile.

    Args:
        event_name: Nom de l'événement.

    Returns:
        list: Liste des participants avec mobile_no.
    """
    from ovh_sms_integration.utils.phone import get_contact_mobile

    participants = []

    event_participants = frappe.get_all(
        "Event Participants",
        filters={"parent": event_name},
        fields=["reference_doctype", "reference_docname"],
    )

    for ep in event_participants:
        if ep.reference_doctype == "Customer":
            try:
                customer = frappe.get_doc("Customer", ep.reference_docname)
                mobile = get_contact_mobile(customer)
                if mobile:
                    participants.append(
                        {
                            "doctype": "Customer",
                            "name": ep.reference_docname,
                            "customer_name": customer.customer_name,
                            "mobile_no": mobile,
                        }
                    )
            except Exception as e:
                frappe.log_error(
                    f"Erreur récupération participant {ep.reference_docname}: {e}"
                )

    return participants


def send_event_reminder_sms(
    event_name: str, test_mode: bool = False
) -> "SMSResult":
    """Envoie un SMS de rappel pour un événement.

    Args:
        event_name: Nom de l'événement.
        test_mode: Si True, simule l'envoi.

    Returns:
        SMSResult: Résultat avec détails par participant.
    """
    from ovh_sms_integration.utils.core import get_ovh_sms_settings, send_sms
    from ovh_sms_integration.utils.templates import format_event_reminder_message

    settings = get_ovh_sms_settings()
    if not settings:
        return {"success": False, "message": _("OVH SMS non activé")}

    event = frappe.get_doc("Event", event_name)
    participants = get_event_participants_with_mobile(event_name)

    if not participants:
        return {"success": False, "message": _("Aucun participant avec mobile")}

    reminder_settings = frappe.get_single("SMS Event Reminder")
    template = reminder_settings.customer_template

    results = {"success": True, "sent": 0, "failed": 0, "details": []}

    for participant in participants:
        message = format_event_reminder_message(
            event.as_dict(), participant.get("customer_name", ""), template
        )

        if test_mode:
            results["details"].append(
                {
                    "participant": participant["name"],
                    "mobile": participant["mobile_no"],
                    "message": message,
                    "status": "test_mode",
                }
            )
            results["sent"] += 1
            continue

        result = send_sms(message, participant["mobile_no"])
        if result and result.get("success"):
            results["sent"] += 1
            log_event_reminder_sent(event_name, participant["name"], "success")
        else:
            results["failed"] += 1
            log_event_reminder_sent(event_name, participant["name"], "failed")

        results["details"].append(
            {
                "participant": participant["name"],
                "mobile": participant["mobile_no"],
                "result": result,
            }
        )

    results["message"] = _("{0} envoyés, {1} échoués").format(
        results["sent"], results["failed"]
    )

    return results


def log_event_reminder_sent(
    event_name: str, participant: str, status: str
) -> None:
    """Enregistre l'envoi d'un rappel dans les logs.

    Args:
        event_name: Nom de l'événement.
        participant: Nom du participant.
        status: Statut de l'envoi (success/failed).
    """
    try:
        frappe.get_doc(
            {
                "doctype": "SMS Log",
                "event": event_name,
                "recipient": participant,
                "status": status,
                "sent_at": datetime.now(),
            }
        ).insert(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(f"Erreur log rappel SMS: {e}")


def process_pending_event_reminders() -> "SMSResult":
    """Traite tous les rappels d'événements en attente.

    Returns:
        SMSResult: Statistiques globales de traitement.
    """
    events = get_events_requiring_reminders()
    total_sent = 0
    total_failed = 0

    for event in events:
        result = send_event_reminder_sms(event["name"])
        total_sent += result.get("sent", 0)
        total_failed += result.get("failed", 0)

    return {
        "success": True,
        "message": _("{0} rappels envoyés, {1} échoués").format(
            total_sent, total_failed
        ),
        "sent": total_sent,
        "failed": total_failed,
    }


def update_reminder_statistics(sent_count: int, failed_count: int) -> None:
    """Met à jour les statistiques de rappels.

    Args:
        sent_count: Nombre de SMS envoyés.
        failed_count: Nombre de SMS échoués.
    """
    try:
        stats = frappe.get_single("SMS Event Reminder")
        stats.total_sent = (stats.total_sent or 0) + sent_count
        stats.total_failed = (stats.total_failed or 0) + failed_count
        stats.last_run = datetime.now()
        stats.save(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(f"Erreur mise à jour statistiques: {e}")

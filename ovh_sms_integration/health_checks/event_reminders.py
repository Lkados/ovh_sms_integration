# -*- coding: utf-8 -*-
"""Vérification des rappels d'événements."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import frappe


def check_event_reminders(health_report: dict[str, Any]) -> None:
    """Vérifie la configuration des rappels d'événements.

    Args:
        health_report: Rapport de santé à remplir avec les résultats.

    Note:
        Vérifie:
        - Activation des rappels
        - Configuration du filtre d'événements
        - Présence d'un template de message
        - Nombre d'événements éligibles aux rappels
    """
    print("\n⏰ Vérification des rappels d'événements...")

    try:
        reminder_settings = frappe.get_single("SMS Event Reminder")

        # Vérification activation
        if reminder_settings.enabled:
            health_report["checks"].append("✅ Rappels d'événements activés")
            print("  ✅ Rappels activés")
        else:
            warning_msg = "⚠️ Rappels d'événements désactivés"
            health_report["warnings"].append(warning_msg)
            print(f"  {warning_msg}")
            return

        # Vérification filtre événements
        if reminder_settings.event_type_filter:
            health_report["checks"].append(
                f"✅ Filtre événements: '{reminder_settings.event_type_filter}'"
            )
            print(f"  ✅ Filtre: '{reminder_settings.event_type_filter}'")
        else:
            warning_msg = "⚠️ Aucun filtre d'événements configuré"
            health_report["warnings"].append(warning_msg)
            print(f"  {warning_msg}")

        # Vérification templates
        if reminder_settings.reminder_message_template:
            health_report["checks"].append("✅ Template de message configuré")
            print("  ✅ Template configuré")
        else:
            warning_msg = "⚠️ Aucun template de message configuré"
            health_report["warnings"].append(warning_msg)
            print(f"  {warning_msg}")

        # Vérification événements éligibles
        events_count = _get_eligible_events_count(reminder_settings.event_type_filter)
        if events_count > 0:
            health_report["checks"].append(
                f"✅ {events_count} événements éligibles trouvés"
            )
            print(f"  ✅ {events_count} événements éligibles")
        else:
            warning_msg = "⚠️ Aucun événement éligible trouvé"
            health_report["warnings"].append(warning_msg)
            print(f"  {warning_msg}")

    except Exception as e:
        error_msg = f"❌ Erreur vérification rappels: {str(e)}"
        health_report["errors"].append(error_msg)
        print(f"  {error_msg}")


def _get_eligible_events_count(event_filter: str | None) -> int:
    """Compte les événements éligibles aux rappels.

    Args:
        event_filter: Filtre de type d'événement.

    Returns:
        int: Nombre d'événements éligibles dans les 30 prochains jours.
    """
    try:
        if not event_filter:
            return 0

        future_date = datetime.now() + timedelta(days=30)

        count = frappe.db.count(
            "Event",
            {
                "subject": ["like", f"%{event_filter}%"],
                "starts_on": ["between", [datetime.now(), future_date]],
                "docstatus": 1,
            },
        )

        return count
    except Exception:
        return 0

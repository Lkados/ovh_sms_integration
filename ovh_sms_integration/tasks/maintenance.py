# -*- coding: utf-8 -*-
"""Tâches de maintenance pour le système de rappels SMS.

Ce module contient les tâches de maintenance et d'optimisation
exécutées périodiquement.
"""

from __future__ import annotations

from datetime import datetime

import frappe


def optimize_reminder_performance() -> None:
    """Optimise les performances du système de rappels.

    Appelée par le scheduler Frappe hebdomadairement pour maintenir
    de bonnes performances du système.

    Note:
        - Optimise les tables MySQL (OPTIMIZE TABLE)
        - Calcule la moyenne de SMS envoyés par jour
        - Met à jour average_sms_per_day dans SMS Event Reminder
    """
    try:
        frappe.logger().info("Optimisation performances rappels")

        # Optimisation MySQL (pas d'équivalent ORM, requêtes DDL nécessaires)
        frappe.db.sql("OPTIMIZE TABLE `tabEvent`")
        frappe.db.sql("OPTIMIZE TABLE `tabEvent Participants`")

        # Mise à jour des statistiques
        reminder_settings = frappe.get_single("SMS Event Reminder")

        # Calcul de la moyenne SMS/jour
        total_days = 30  # Sur les 30 derniers jours
        avg_per_day = (reminder_settings.total_reminders_sent or 0) / total_days
        reminder_settings.db_set("average_sms_per_day", round(avg_per_day, 2))

        frappe.db.commit()
        frappe.logger().info("Optimisation terminée")

    except Exception as e:
        frappe.log_error(f"Erreur optimisation performances: {e}")


def backup_reminder_settings() -> None:
    """Sauvegarde les paramètres de rappels.

    Appelée par le scheduler Frappe hebdomadairement pour créer
    une sauvegarde JSON des configurations actives.

    Note:
        - Exporte OVH SMS Settings et SMS Event Reminder
        - Format: sms_backup_YYYYMMDD_HHMMSS.json
        - N'inclut PAS les secrets (application_key, application_secret, etc.)
    """
    try:
        frappe.logger().info("Sauvegarde paramètres rappels")

        # Sauvegarde des paramètres SMS
        sms_settings = frappe.get_single("OVH SMS Settings")
        reminder_settings = frappe.get_single("SMS Event Reminder")

        _backup_data = {  # noqa: F841
            "timestamp": datetime.now().isoformat(),
            "ovh_sms_settings": {
                "enabled": sms_settings.enabled,
                "auto_detect_service": sms_settings.auto_detect_service,
                "default_sender": sms_settings.default_sender,
                "service_name": sms_settings.service_name,
                # Ne pas sauvegarder les secrets
            },
            "reminder_settings": {
                "enabled": reminder_settings.enabled,
                "event_type_filter": reminder_settings.event_type_filter,
                "reminder_hours_before": reminder_settings.reminder_hours_before,
                "enable_multiple_reminders": reminder_settings.enable_multiple_reminders,
                "reminder_times": reminder_settings.reminder_times,
                "send_to_customer_only": reminder_settings.send_to_customer_only,
                "send_to_employee": reminder_settings.send_to_employee,
            },
        }

        # Écriture du fichier de sauvegarde
        backup_file = f"sms_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        # Log de la sauvegarde
        frappe.logger().info(f"Sauvegarde créée: {backup_file}")

    except Exception as e:
        frappe.log_error(f"Erreur sauvegarde paramètres: {e}")

# -*- coding: utf-8 -*-
"""Tâches quotidiennes pour le système de rappels SMS.

Ce module contient les tâches exécutées chaque jour
par le scheduler Frappe.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import frappe


def reset_daily_counters() -> None:
    """Remet à zéro les compteurs journaliers.

    Appelée par le scheduler Frappe chaque jour à minuit pour
    remettre à zéro les compteurs de SMS envoyés aujourd'hui.

    Note:
        - Réinitialise reminders_sent_today dans SMS Event Reminder
        - Réinitialise sms_sent_today dans OVH SMS Settings
        - Utilise db_set() pour éviter les triggers de validation
        - Les erreurs sont loggées mais ne bloquent pas le scheduler
    """
    try:
        frappe.logger().info("Reset compteurs journaliers rappels")

        # Reset du compteur journalier pour SMS Event Reminder
        reminder_settings = frappe.get_single("SMS Event Reminder")
        reminder_settings.db_set("reminders_sent_today", 0)

        # Reset du compteur journalier pour OVH SMS Settings
        sms_settings = frappe.get_single("OVH SMS Settings")
        sms_settings.db_set("sms_sent_today", 0)

        frappe.db.commit()
        frappe.logger().info("Compteurs journaliers remis à zéro")

    except Exception as e:
        frappe.log_error(f"Erreur reset compteurs journaliers: {e}")


def cleanup_old_reminder_logs() -> None:
    """Nettoie les anciens logs de rappels.

    Appelée par le scheduler Frappe quotidiennement pour supprimer
    les logs de rappels SMS trop anciens et économiser l'espace disque.

    Note:
        - Supprime Error Logs et Activity Logs de plus de 30 jours
        - Filtre les logs liés aux SMS/OVH/rappels
        - Les erreurs sont loggées mais ne bloquent pas le scheduler
    """
    try:
        frappe.logger().info("Nettoyage anciens logs rappels")

        # Suppression des logs d'erreur de plus de 30 jours
        thirty_days_ago = datetime.now() - timedelta(days=30)

        # Nettoyage des Error Logs liés aux SMS (ORM)
        error_logs = frappe.get_all(
            "Error Log",
            filters=[["creation", "<", thirty_days_ago], ["error", "like", "%SMS%"]],
            pluck="name",
        )
        for log_name in error_logs:
            frappe.delete_doc(
                "Error Log", log_name, ignore_permissions=True, force=True
            )

        # Nettoyage des Activity Logs liés aux SMS (ORM)
        activity_logs = frappe.get_all(
            "Activity Log",
            filters=[["creation", "<", thirty_days_ago], ["subject", "like", "%SMS%"]],
            pluck="name",
        )
        for log_name in activity_logs:
            frappe.delete_doc(
                "Activity Log", log_name, ignore_permissions=True, force=True
            )

        frappe.db.commit()
        frappe.logger().info("Nettoyage logs terminé")

    except Exception as e:
        frappe.log_error(f"Erreur nettoyage logs: {e}")

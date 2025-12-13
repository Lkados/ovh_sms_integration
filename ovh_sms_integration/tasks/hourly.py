# -*- coding: utf-8 -*-
"""Tâches horaires pour le système de rappels SMS.

Ce module contient les tâches exécutées toutes les heures
par le scheduler Frappe.
"""

from __future__ import annotations

import frappe


def check_event_reminders_hourly() -> None:
    """Tâche horaire pour vérifier et envoyer les rappels d'événements.

    Appelée par le scheduler Frappe toutes les heures pour traiter
    les rappels d'événements automatiques configurés.

    Note:
        - Vérifie que reminder_settings.enabled = True
        - Vérifie should_send_now() pour respecter heures ouvrables
        - Délègue à reminder_settings.send_event_reminders()
        - Les erreurs sont loggées mais ne bloquent pas le scheduler
    """
    try:
        frappe.logger().info("Début vérification rappels événements - Horaire")

        # Récupération des paramètres
        reminder_settings = frappe.get_single("SMS Event Reminder")

        if not reminder_settings.enabled:
            frappe.logger().info("Rappels d'événements désactivés")
            return

        # Vérification si c'est le bon moment pour envoyer
        if not reminder_settings.should_send_now():
            frappe.logger().info("Hors heures d'envoi configurées")
            return

        # Traitement des rappels
        reminder_settings.send_event_reminders()

        frappe.logger().info("Fin vérification rappels événements - Horaire")

    except Exception as e:
        frappe.log_error(f"Erreur tâche horaire rappels: {e}")

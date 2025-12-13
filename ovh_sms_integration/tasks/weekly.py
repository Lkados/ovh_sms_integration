# -*- coding: utf-8 -*-
"""Tâches hebdomadaires pour le système de rappels SMS.

Ce module contient les tâches exécutées chaque semaine
par le scheduler Frappe.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import frappe
from frappe import _


def send_weekly_reminder_report() -> None:
    """Envoie un rapport hebdomadaire des rappels.

    Appelée par le scheduler Frappe chaque lundi pour envoyer
    un rapport par email aux administrateurs système.

    Note:
        - Génère un rapport HTML avec statistiques de la semaine
        - Envoie aux utilisateurs avec role "System Manager"
        - Inclut: événements programmés, rappels envoyés, échecs
        - Utilise templates Jinja pour l'HTML
    """
    try:
        frappe.logger().info("Génération rapport hebdomadaire rappels")

        # Calcul des statistiques de la semaine
        weekly_stats = _calculate_weekly_stats()

        # Génération du rapport
        report_content = _generate_weekly_report(weekly_stats)

        # Envoi par email aux administrateurs (optionnel)
        _send_report_to_administrators(report_content)

        frappe.logger().info("Rapport hebdomadaire généré")

    except Exception as e:
        frappe.log_error(f"Erreur génération rapport hebdomadaire: {e}")


def _calculate_weekly_stats() -> dict[str, Any]:
    """Calcule les statistiques de la semaine.

    Returns:
        dict[str, Any]: Statistiques hebdomadaires avec:
            - events_scheduled: Nombre d'événements programmés
            - reminders_sent: Rappels envoyés cette semaine
            - total_reminders: Total de tous les rappels
            - failed_reminders: Nombre de rappels échoués
            - week_start: Date de début (format DD/MM/YYYY)
            - week_end: Date de fin (format DD/MM/YYYY)
    """
    try:
        week_ago = datetime.now() - timedelta(days=7)

        # Statistiques des rappels
        reminder_settings = frappe.get_single("SMS Event Reminder")

        # Événements traités cette semaine (ORM Frappe)
        events_count = frappe.db.count(
            "Event",
            filters={
                "starts_on": ["between", [week_ago, datetime.now()]],
                "subject": ["like", f"%{reminder_settings.event_type_filter}%"],
                "docstatus": 1,
            },
        )

        # Rappels envoyés (estimation basée sur les logs)
        reminder_logs_count = _get_reminder_logs_count(week_ago)

        return {
            "events_scheduled": events_count,
            "reminders_sent": reminder_logs_count,
            "total_reminders": reminder_settings.total_reminders_sent or 0,
            "failed_reminders": reminder_settings.failed_reminders_count or 0,
            "week_start": week_ago.strftime("%d/%m/%Y"),
            "week_end": datetime.now().strftime("%d/%m/%Y"),
        }

    except Exception as e:
        frappe.log_error(f"Erreur calcul statistiques hebdomadaires: {e}")
        return {}


def _get_reminder_logs_count(since_date: datetime) -> int:
    """Compte les rappels envoyés depuis une date.

    Args:
        since_date: Date de début pour le comptage.

    Returns:
        int: Nombre de rappels envoyés depuis cette date.
    """
    try:
        # Recherche dans les logs système (ORM Frappe)
        logs_count = frappe.db.count(
            "Error Log",
            filters={
                "creation": [">=", since_date],
                "error": ["like", "%Rappel envoyé%"],
            },
        )

        return logs_count

    except Exception as e:
        frappe.log_error(f"Erreur comptage logs rappels: {e}")
        return 0


def _generate_weekly_report(stats: dict[str, Any]) -> str:
    """Génère le contenu du rapport hebdomadaire.

    Args:
        stats: Statistiques hebdomadaires à inclure dans le rapport.

    Returns:
        str: Contenu HTML du rapport formaté.
    """
    try:
        # Générer le tableau des événements à venir
        upcoming_events_html = _get_upcoming_events_table()

        # Rendre le template Jinja
        report = frappe.render_template(
            "ovh_sms_integration/templates/emails/weekly_reminder_report.html",
            {
                "stats": stats,
                "upcoming_events_html": upcoming_events_html,
                "generation_date": datetime.now().strftime("%d/%m/%Y à %H:%M"),
            },
        )

        return report

    except Exception as e:
        frappe.log_error(f"Erreur génération contenu rapport: {e}")
        return "Erreur lors de la génération du rapport"


def _get_upcoming_events_table() -> str:
    """Génère le tableau des prochains événements.

    Returns:
        str: Tableau HTML des 10 prochains événements avec rappels configurés.
    """
    try:
        reminder_settings = frappe.get_single("SMS Event Reminder")

        # Récupération des prochains événements (ORM Frappe)
        upcoming_events = frappe.get_all(
            "Event",
            filters={
                "starts_on": [
                    "between",
                    [datetime.now(), datetime.now() + timedelta(days=7)],
                ],
                "subject": ["like", f"%{reminder_settings.event_type_filter}%"],
                "docstatus": 1,
            },
            fields=["name", "subject", "starts_on", "description"],
            order_by="starts_on asc",
            limit=10,
        )

        # Préparer les données pour le template
        events_data = []
        for event in upcoming_events:
            start_date = (
                event.starts_on.strftime("%d/%m/%Y %H:%M") if event.starts_on else "N/A"
            )
            description = (event.description or "")[:50]
            if len(event.description or "") > 50:
                description += "..."

            events_data.append(
                {
                    "subject": event.subject,
                    "start_date": start_date,
                    "description_preview": description,
                }
            )

        # Rendre le template Jinja
        table = frappe.render_template(
            "ovh_sms_integration/templates/emails/upcoming_events_table.html",
            {"events": events_data},
        )

        return table

    except Exception as e:
        frappe.log_error(f"Erreur génération tableau événements: {e}")
        error_msg = _("Erreur lors de la récupération des événements.")
        return frappe.render_template(
            "ovh_sms_integration/templates/includes/error_message.html",
            {"message": error_msg},
        )


def _send_report_to_administrators(report_content: str) -> None:
    """Envoie le rapport aux administrateurs par email.

    Args:
        report_content: Contenu HTML du rapport à envoyer.
    """
    try:
        # Récupération des utilisateurs avec role System Manager (ORM Frappe)
        system_managers = frappe.get_all(
            "Has Role",
            filters={"role": "System Manager", "parenttype": "User"},
            fields=["parent"],
            distinct=True,
        )

        if not system_managers:
            frappe.logger().info("Aucun administrateur trouvé pour l'envoi du rapport")
            return

        # Récupération des emails des utilisateurs actifs
        recipients = []
        for role_assignment in system_managers:
            user = frappe.get_doc("User", role_assignment.parent)
            if user.enabled and user.email and user.email != "Administrator":
                recipients.append(user.email)

        # Envoi de l'email
        frappe.sendmail(
            recipients=recipients,
            subject=f"Rapport Hebdomadaire - Rappels SMS {datetime.now().strftime('%d/%m/%Y')}",
            message=report_content,
            header=["Rapport SMS", "blue"],
        )

        frappe.logger().info(f"Rapport envoyé à {len(recipients)} administrateur(s)")

    except Exception as e:
        frappe.log_error(f"Erreur envoi rapport: {e}")

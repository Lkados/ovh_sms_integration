# -*- coding: utf-8 -*-
"""Script de vérification de santé du système OVH SMS Integration.

Ce module contient les outils de diagnostic et de vérification
pour s'assurer que tous les composants fonctionnent correctement.

Note:
    Ce fichier réexporte les fonctions depuis les sous-modules pour
    maintenir la rétrocompatibilité.

    Les implémentations sont dans:
    - health_checks/doctypes.py: Vérification DocTypes
    - health_checks/ovh_settings.py: Vérification paramètres OVH
    - health_checks/event_reminders.py: Vérification rappels
    - health_checks/scheduler.py: Vérification scheduler
    - health_checks/permissions.py: Vérification permissions
    - health_checks/recent_activity.py: Vérification activité récente
    - health_checks/database.py: Vérification base de données
    - health_checks/report.py: Génération et affichage rapports
    - health_checks/runner.py: Exécuteur principal
"""

# Réexportation pour rétrocompatibilité
from ovh_sms_integration.health_checks.database import check_database_health
from ovh_sms_integration.health_checks.doctypes import check_doctypes
from ovh_sms_integration.health_checks.event_reminders import check_event_reminders
from ovh_sms_integration.health_checks.ovh_settings import check_ovh_settings
from ovh_sms_integration.health_checks.permissions import check_permissions
from ovh_sms_integration.health_checks.recent_activity import check_recent_activity
from ovh_sms_integration.health_checks.report import (
    display_health_report,
    save_health_report,
)
from ovh_sms_integration.health_checks.runner import (
    run_health_check,
    run_health_check_api,
)
from ovh_sms_integration.health_checks.scheduler import check_scheduler

__all__ = [
    "run_health_check",
    "run_health_check_api",
    "check_doctypes",
    "check_ovh_settings",
    "check_event_reminders",
    "check_scheduler",
    "check_permissions",
    "check_recent_activity",
    "check_database_health",
    "display_health_report",
    "save_health_report",
]


if __name__ == "__main__":
    # Exécution en mode standalone
    import frappe

    try:
        frappe.init(site="test_site")
        frappe.connect()

        health_report = run_health_check()

        # Sauvegarde optionnelle
        save_health_report(health_report)

        frappe.destroy()

    except Exception as e:
        print(f"❌ Erreur critique: {e}")
        exit(1)

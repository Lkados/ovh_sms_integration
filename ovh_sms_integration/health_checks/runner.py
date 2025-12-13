# -*- coding: utf-8 -*-
"""Exécuteur principal des vérifications de santé."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import frappe

from ovh_sms_integration.health_checks.database import check_database_health
from ovh_sms_integration.health_checks.doctypes import check_doctypes
from ovh_sms_integration.health_checks.event_reminders import check_event_reminders
from ovh_sms_integration.health_checks.ovh_settings import check_ovh_settings
from ovh_sms_integration.health_checks.permissions import check_permissions
from ovh_sms_integration.health_checks.recent_activity import check_recent_activity
from ovh_sms_integration.health_checks.report import display_health_report
from ovh_sms_integration.health_checks.scheduler import check_scheduler


def run_health_check() -> dict[str, Any]:
    """Exécute une vérification complète du système.

    Returns:
        dict[str, Any]: Rapport de santé complet avec:
            - timestamp: Date/heure de la vérification
            - overall_status: "healthy", "warning" ou "error"
            - checks: Liste des vérifications réussies
            - warnings: Liste des avertissements
            - errors: Liste des erreurs

    Note:
        Exécute toutes les vérifications:
        1. DocTypes requis
        2. Paramètres OVH
        3. Rappels d'événements
        4. Scheduler
        5. Permissions
        6. Activité récente
        7. Base de données
    """
    print("🔍 Vérification de santé - OVH SMS Integration")
    print("=" * 60)

    health_report: dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "overall_status": "healthy",
        "checks": [],
        "warnings": [],
        "errors": [],
    }

    try:
        # 1. Vérification des DocTypes
        check_doctypes(health_report)

        # 2. Vérification des paramètres OVH
        check_ovh_settings(health_report)

        # 3. Vérification des rappels d'événements
        check_event_reminders(health_report)

        # 4. Vérification du scheduler
        check_scheduler(health_report)

        # 5. Vérification des permissions
        check_permissions(health_report)

        # 6. Vérification des tâches récentes
        check_recent_activity(health_report)

        # 7. Vérification de la base de données
        check_database_health(health_report)

    except Exception as e:
        health_report["errors"].append(
            f"Erreur générale lors de la vérification: {str(e)}"
        )
        health_report["overall_status"] = "error"

    # Détermination du statut global
    if health_report["errors"]:
        health_report["overall_status"] = "error"
    elif health_report["warnings"]:
        health_report["overall_status"] = "warning"

    # Affichage du rapport
    display_health_report(health_report)

    return health_report


@frappe.whitelist()
def run_health_check_api() -> dict[str, Any]:
    """API pour exécuter la vérification de santé.

    Returns:
        dict[str, Any]: Rapport de santé ou erreur.

    Note:
        Exposée via @frappe.whitelist() pour appel depuis l'interface web.
    """
    try:
        health_report = run_health_check()
        return health_report
    except Exception as e:
        frappe.log_error(f"Erreur health check API: {e}")
        return {
            "overall_status": "error",
            "errors": [str(e)],
            "timestamp": datetime.now().isoformat(),
        }

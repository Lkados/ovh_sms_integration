# -*- coding: utf-8 -*-
"""Module de vérification de santé du système OVH SMS Integration.

Ce module fournit des outils de diagnostic et de vérification
pour s'assurer que tous les composants fonctionnent correctement.
"""

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

# -*- coding: utf-8 -*-
"""Tâches planifiées pour ovh_sms_integration.

Ce module contient les tâches schedulées (cron jobs) pour le système de rappels SMS.
Il fournit les fonctionnalités de:
- Vérification horaire des rappels d'événements
- Réinitialisation quotidienne des compteurs
- Nettoyage des anciens logs
- Rapports hebdomadaires par email
- Vérifications de santé du système
- Optimisation de performance
- Sauvegarde des configurations
"""

from ovh_sms_integration.tasks.daily import (
    cleanup_old_reminder_logs,
    reset_daily_counters,
)
from ovh_sms_integration.tasks.health import check_reminder_system_health
from ovh_sms_integration.tasks.hourly import check_event_reminders_hourly
from ovh_sms_integration.tasks.maintenance import (
    backup_reminder_settings,
    optimize_reminder_performance,
)
from ovh_sms_integration.tasks.weekly import send_weekly_reminder_report

__all__ = [
    "check_event_reminders_hourly",
    "reset_daily_counters",
    "cleanup_old_reminder_logs",
    "send_weekly_reminder_report",
    "check_reminder_system_health",
    "optimize_reminder_performance",
    "backup_reminder_settings",
]

# -*- coding: utf-8 -*-
"""Vérification du scheduler Frappe."""

from __future__ import annotations

from typing import Any

import frappe


def check_scheduler(health_report: dict[str, Any]) -> None:
    """Vérifie que le scheduler fonctionne.

    Args:
        health_report: Rapport de santé à remplir avec les résultats.

    Note:
        Vérifie:
        - Statut du scheduler (activé/désactivé)
        - Disponibilité des tâches planifiées requises
    """
    print("\n⚙️ Vérification du scheduler...")

    try:
        # Vérification du statut du scheduler
        scheduler_enabled = not frappe.conf.get("pause_scheduler", False)

        if scheduler_enabled:
            health_report["checks"].append("✅ Scheduler activé")
            print("  ✅ Scheduler activé")
        else:
            error_msg = "❌ Scheduler désactivé"
            health_report["errors"].append(error_msg)
            print(f"  {error_msg}")

        # Vérification des tâches configurées
        required_tasks = [
            (
                "ovh_sms_integration.ovh_sms_integration.doctype."
                "sms_event_reminder.sms_event_reminder.process_event_reminders"
            ),
            "ovh_sms_integration.tasks.check_event_reminders_hourly",
            "ovh_sms_integration.tasks.reset_daily_counters",
        ]

        for task in required_tasks:
            _verify_task_available(task, health_report)

    except Exception as e:
        error_msg = f"❌ Erreur vérification scheduler: {str(e)}"
        health_report["errors"].append(error_msg)
        print(f"  {error_msg}")


def _verify_task_available(task: str, health_report: dict[str, Any]) -> None:
    """Vérifie qu'une tâche planifiée est disponible.

    Args:
        task: Chemin complet de la tâche (module.fonction).
        health_report: Rapport de santé à remplir.
    """
    try:
        # Tentative d'importation de la fonction
        module_path, function_name = task.rsplit(".", 1)
        module = frappe.get_module(module_path)
        if hasattr(module, function_name):
            health_report["checks"].append(f"✅ Tâche {function_name} disponible")
            print(f"  ✅ {function_name}")
        else:
            warning_msg = f"⚠️ Fonction {function_name} introuvable"
            health_report["warnings"].append(warning_msg)
            print(f"  {warning_msg}")
    except Exception as e:
        warning_msg = f"⚠️ Erreur importation {task}: {str(e)}"
        health_report["warnings"].append(warning_msg)
        print(f"  {warning_msg}")

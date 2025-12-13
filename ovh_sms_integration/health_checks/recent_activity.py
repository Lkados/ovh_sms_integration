# -*- coding: utf-8 -*-
"""Vérification de l'activité récente du système."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import frappe


def check_recent_activity(health_report: dict[str, Any]) -> None:
    """Vérifie l'activité récente du système.

    Args:
        health_report: Rapport de santé à remplir avec les résultats.

    Note:
        Vérifie:
        - Date du dernier rappel envoyé
        - Total des rappels envoyés
        - Nombre d'échecs
        - Taux d'échec (alerte si > 10%)
    """
    print("\n📊 Vérification de l'activité récente...")

    try:
        # Vérification des derniers rappels
        reminder_settings = frappe.get_single("SMS Event Reminder")

        if reminder_settings.last_reminder_sent:
            last_sent = reminder_settings.last_reminder_sent
            hours_ago = (datetime.now() - last_sent).total_seconds() / 3600

            if hours_ago < 24:
                health_report["checks"].append(
                    f"✅ Dernier rappel: il y a {hours_ago:.1f}h"
                )
                print(f"  ✅ Dernier rappel: il y a {hours_ago:.1f}h")
            else:
                warning_msg = f"⚠️ Dernier rappel: il y a {hours_ago:.1f}h"
                health_report["warnings"].append(warning_msg)
                print(f"  {warning_msg}")
        else:
            warning_msg = "⚠️ Aucun rappel envoyé récemment"
            health_report["warnings"].append(warning_msg)
            print(f"  {warning_msg}")

        # Statistiques
        total_sent = reminder_settings.total_reminders_sent or 0
        failed_count = reminder_settings.failed_reminders_count or 0

        health_report["checks"].append(f"✅ Total rappels: {total_sent}")
        health_report["checks"].append(f"✅ Échecs: {failed_count}")
        print(f"  ✅ Total rappels: {total_sent}")
        print(f"  ✅ Échecs: {failed_count}")

        # Taux d'échec
        if total_sent > 0:
            failure_rate = (failed_count / total_sent) * 100
            if failure_rate > 10:
                warning_msg = f"⚠️ Taux d'échec élevé: {failure_rate:.1f}%"
                health_report["warnings"].append(warning_msg)
                print(f"  {warning_msg}")
            else:
                health_report["checks"].append(f"✅ Taux d'échec: {failure_rate:.1f}%")
                print(f"  ✅ Taux d'échec: {failure_rate:.1f}%")

    except Exception as e:
        error_msg = f"❌ Erreur vérification activité: {str(e)}"
        health_report["errors"].append(error_msg)
        print(f"  {error_msg}")

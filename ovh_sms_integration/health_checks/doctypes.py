# -*- coding: utf-8 -*-
"""Vérification des DocTypes pour OVH SMS Integration."""

from __future__ import annotations

from typing import Any

import frappe


def check_doctypes(health_report: dict[str, Any]) -> None:
    """Vérifie que tous les DocTypes nécessaires existent.

    Args:
        health_report: Rapport de santé à remplir avec les résultats.

    Note:
        Vérifie l'existence des DocTypes:
        - OVH SMS Settings
        - SMS Event Reminder
    """
    print("\n📋 Vérification des DocTypes...")

    required_doctypes = ["OVH SMS Settings", "SMS Event Reminder"]

    for doctype in required_doctypes:
        try:
            if frappe.db.exists("DocType", doctype):
                health_report["checks"].append(f"✅ DocType {doctype} existe")
                print(f"  ✅ {doctype}")
            else:
                error_msg = f"❌ DocType {doctype} manquant"
                health_report["errors"].append(error_msg)
                print(f"  {error_msg}")
        except Exception as e:
            error_msg = f"❌ Erreur vérification {doctype}: {str(e)}"
            health_report["errors"].append(error_msg)
            print(f"  {error_msg}")

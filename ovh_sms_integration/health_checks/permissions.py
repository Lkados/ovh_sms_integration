# -*- coding: utf-8 -*-
"""Vérification des permissions pour OVH SMS Integration."""

from __future__ import annotations

from typing import Any

import frappe


def check_permissions(health_report: dict[str, Any]) -> None:
    """Vérifie les permissions des rôles.

    Args:
        health_report: Rapport de santé à remplir avec les résultats.

    Note:
        Vérifie:
        - Existence des rôles SMS Manager et SMS User
        - Présence de permissions sur les DocTypes
    """
    print("\n🔒 Vérification des permissions...")

    try:
        required_roles = ["SMS Manager", "SMS User"]

        for role in required_roles:
            if frappe.db.exists("Role", role):
                health_report["checks"].append(f"✅ Rôle {role} existe")
                print(f"  ✅ Rôle {role}")
            else:
                warning_msg = f"⚠️ Rôle {role} manquant"
                health_report["warnings"].append(warning_msg)
                print(f"  {warning_msg}")

        # Vérification permissions DocTypes
        doctypes_to_check = ["OVH SMS Settings", "SMS Event Reminder"]
        for doctype in doctypes_to_check:
            perms = frappe.db.count("DocPerm", {"parent": doctype})
            if perms > 0:
                health_report["checks"].append(f"✅ Permissions {doctype}: {perms}")
                print(f"  ✅ {doctype}: {perms} permissions")
            else:
                warning_msg = f"⚠️ Aucune permission pour {doctype}"
                health_report["warnings"].append(warning_msg)
                print(f"  {warning_msg}")

    except Exception as e:
        error_msg = f"❌ Erreur vérification permissions: {str(e)}"
        health_report["errors"].append(error_msg)
        print(f"  {error_msg}")

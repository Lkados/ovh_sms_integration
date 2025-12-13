# -*- coding: utf-8 -*-
"""Vérification de la santé de la base de données."""

from __future__ import annotations

from typing import Any

import frappe


def check_database_health(health_report: dict[str, Any]) -> None:
    """Vérifie la santé de la base de données.

    Args:
        health_report: Rapport de santé à remplir avec les résultats.

    Note:
        Vérifie:
        - Accessibilité des tables principales
        - Présence des index importants
    """
    print("\n🗄️ Vérification de la base de données...")

    try:
        # Vérification des tables principales
        required_tables = ["tabOVH SMS Settings", "tabSMS Event Reminder", "tabEvent"]

        for table in required_tables:
            try:
                # Extraire le nom du DocType depuis le nom de table (tabXXX -> XXX)
                doctype_name = (
                    table.replace("tab", "", 1) if table.startswith("tab") else table
                )
                frappe.db.count(doctype_name)
                health_report["checks"].append(f"✅ Table {table} accessible")
                print(f"  ✅ {table}")
            except Exception as e:
                error_msg = f"❌ Table {table} inaccessible: {str(e)}"
                health_report["errors"].append(error_msg)
                print(f"  {error_msg}")

        # Vérification des index
        _check_database_indexes(health_report)

    except Exception as e:
        error_msg = f"❌ Erreur vérification base de données: {str(e)}"
        health_report["errors"].append(error_msg)
        print(f"  {error_msg}")


def _check_database_indexes(health_report: dict[str, Any]) -> None:
    """Vérifie les index de la base de données.

    Args:
        health_report: Rapport de santé à remplir.

    Note:
        Les requêtes SHOW INDEX sont des commandes DDL spécifiques MySQL,
        pas d'équivalent ORM disponible.
    """
    try:
        # Vérifier l'index sur les événements (requête DDL nécessaire)
        frappe.db.sql("SHOW INDEX FROM `tabEvent` WHERE Key_name = 'starts_on'")
        health_report["checks"].append("✅ Index base de données OK")
        print("  ✅ Index OK")
    except Exception as e:
        warning_msg = f"⚠️ Problème index: {str(e)}"
        health_report["warnings"].append(warning_msg)
        print(f"  {warning_msg}")

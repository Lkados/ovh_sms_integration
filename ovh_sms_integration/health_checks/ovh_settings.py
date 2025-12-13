# -*- coding: utf-8 -*-
"""Vérification des paramètres OVH SMS."""

from __future__ import annotations

from typing import Any

import frappe


def check_ovh_settings(health_report: dict[str, Any]) -> None:
    """Vérifie la configuration OVH SMS.

    Args:
        health_report: Rapport de santé à remplir avec les résultats.

    Note:
        Vérifie:
        - Activation de l'intégration OVH SMS
        - Présence des champs obligatoires (application_key, application_secret, consumer_key)
        - Test de connexion à l'API OVH
    """
    print("\n🔧 Vérification des paramètres OVH...")

    try:
        settings = frappe.get_single("OVH SMS Settings")

        # Vérification activation
        if settings.enabled:
            health_report["checks"].append("✅ OVH SMS activé")
            print("  ✅ OVH SMS activé")
        else:
            warning_msg = "⚠️ OVH SMS désactivé"
            health_report["warnings"].append(warning_msg)
            print(f"  {warning_msg}")
            return

        # Vérification des champs obligatoires
        required_fields = ["application_key", "application_secret", "consumer_key"]
        for field in required_fields:
            if field == "application_secret" or field == "consumer_key":
                value = settings.get_password(field)
            else:
                value = getattr(settings, field, None)

            if value:
                health_report["checks"].append(f"✅ {field} configuré")
                print(f"  ✅ {field} configuré")
            else:
                error_msg = f"❌ {field} manquant"
                health_report["errors"].append(error_msg)
                print(f"  {error_msg}")

        # Test de connexion
        print("  📡 Test de connexion OVH...")
        connection_result = settings.test_connection()
        if connection_result.get("success"):
            health_report["checks"].append("✅ Connexion OVH réussie")
            print("    ✅ Connexion réussie")
        else:
            error_msg = f"❌ Connexion OVH échouée: {connection_result.get('message')}"
            health_report["errors"].append(error_msg)
            print(f"    {error_msg}")

    except Exception as e:
        error_msg = f"❌ Erreur vérification OVH: {str(e)}"
        health_report["errors"].append(error_msg)
        print(f"  {error_msg}")

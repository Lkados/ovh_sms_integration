# -*- coding: utf-8 -*-
"""Tâches de vérification de santé du système de rappels SMS.

Ce module contient les tâches de monitoring et de vérification
de la santé du système.
"""

from __future__ import annotations

import frappe


def check_reminder_system_health() -> bool:
    """Vérifie la santé du système de rappels.

    Appelée par le scheduler Frappe quotidiennement pour détecter
    les problèmes potentiels du système de rappels.

    Returns:
        bool: True si le système est en bonne santé, False sinon.

    Note:
        - Vérifie: OVH settings, connexion API, configurations rappels
        - Logue les problèmes détectés via frappe.log_error()
        - Les erreurs sont loggées mais ne bloquent pas le scheduler
    """
    try:
        health_issues = []

        # Vérification des paramètres OVH SMS
        health_issues.extend(_check_ovh_settings())

        # Vérification des paramètres de rappels
        health_issues.extend(_check_reminder_settings())

        # Log des problèmes trouvés
        if health_issues:
            frappe.log_error(
                f"Problèmes système rappels SMS: {'; '.join(health_issues)}"
            )
        else:
            frappe.logger().info("Système de rappels SMS en bonne santé")

        return len(health_issues) == 0

    except Exception as e:
        frappe.log_error(f"Erreur vérification santé système: {e}")
        return False


def _check_ovh_settings() -> list[str]:
    """Vérifie les paramètres OVH SMS.

    Returns:
        list[str]: Liste des problèmes détectés.
    """
    issues = []
    try:
        sms_settings = frappe.get_single("OVH SMS Settings")
        if not sms_settings.enabled:
            issues.append("OVH SMS Integration désactivé")

        # Test de connexion
        connection_test = sms_settings.test_connection()
        if not connection_test.get("success"):
            issues.append(f"Problème connexion OVH: {connection_test.get('message')}")

    except Exception as e:
        issues.append(f"Erreur vérification OVH SMS: {str(e)}")

    return issues


def _check_reminder_settings() -> list[str]:
    """Vérifie les paramètres de rappels.

    Returns:
        list[str]: Liste des problèmes détectés.
    """
    issues = []
    try:
        reminder_settings = frappe.get_single("SMS Event Reminder")
        if not reminder_settings.enabled:
            issues.append("Rappels d'événements désactivés")

        if not reminder_settings.event_type_filter:
            issues.append("Aucun type d'événement configuré")

    except Exception as e:
        issues.append(f"Erreur vérification rappels: {str(e)}")

    return issues

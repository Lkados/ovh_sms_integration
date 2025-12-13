# -*- coding: utf-8 -*-
"""Permission query functions for SMS campaigns.

Ce module gère les conditions de requête et validation des permissions.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
from frappe import _

if TYPE_CHECKING:
    from frappe.model.document import Document


def get_campaign_permission_query_conditions(user: str | None = None) -> str:
    """Génère les conditions SQL pour filtrer les campagnes SMS par permissions.

    Args:
        user: Nom d'utilisateur optionnel.

    Returns:
        str: Condition SQL pour filtrer les campagnes accessibles.
    """
    if not user:
        user = frappe.session.user

    if "System Manager" in frappe.get_roles(user):
        return ""

    if "SMS Manager" in frappe.get_roles(user):
        user_company = frappe.db.get_value("User", user, "company")
        if user_company:
            return (
                f"(`tabSMS Pricing Campaign`.company = '{user_company}' "
                "or `tabSMS Pricing Campaign`.company is null)"
            )
        return ""

    if "SMS User" in frappe.get_roles(user):
        return f"`tabSMS Pricing Campaign`.owner = '{user}'"

    return "1=0"


def has_campaign_permission(doc: "Document", user: str | None = None) -> bool:
    """Vérifie si l'utilisateur a les permissions sur une campagne.

    Args:
        doc: Document SMS Pricing Campaign à vérifier.
        user: Nom d'utilisateur optionnel.

    Returns:
        bool: True si l'utilisateur a accès, False sinon.
    """
    if not user:
        user = frappe.session.user

    if "System Manager" in frappe.get_roles(user):
        return True

    if "SMS Manager" in frappe.get_roles(user):
        user_company = frappe.db.get_value("User", user, "company")
        if user_company and doc.company == user_company:
            return True
        if not doc.company:
            return True

    if "SMS User" in frappe.get_roles(user):
        return doc.owner == user

    return False


def validate_sms_permissions(doc: "Document", method: str) -> None:
    """Validation des permissions lors de la sauvegarde.

    Args:
        doc: Document SMS Pricing Campaign à valider.
        method: Nom de la méthode.

    Raises:
        frappe.exceptions.PermissionError: Si permissions insuffisantes.
    """
    if frappe.flags.in_install or frappe.flags.in_migrate:
        return

    if not has_campaign_permission(doc):
        frappe.throw(_("Permissions insuffisantes pour cette campagne"))


def validate_sms_sending_permission(user: str | None = None) -> None:
    """Vérifie les permissions d'envoi de SMS.

    Args:
        user: Nom d'utilisateur optionnel.

    Raises:
        frappe.exceptions.PermissionError: Si l'utilisateur n'a pas les permissions.
    """
    from ovh_sms_integration.permissions.quota import check_user_sms_quota

    if not user:
        user = frappe.session.user

    required_roles = ["SMS Manager", "SMS User", "System Manager"]
    user_roles = frappe.get_roles(user)

    if not any(role in user_roles for role in required_roles):
        frappe.throw(_("Permission d'envoi SMS requise"))

    check_user_sms_quota(user)

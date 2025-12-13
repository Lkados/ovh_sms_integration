# -*- coding: utf-8 -*-
"""Quota management for SMS campaigns.

Ce module gère les quotas journaliers par utilisateur.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import frappe
from frappe import _


def check_user_sms_quota(user: str) -> int:
    """Vérifie le quota SMS de l'utilisateur.

    Args:
        user: Nom d'utilisateur.

    Returns:
        int: Nombre de SMS restants dans le quota journalier.

    Raises:
        frappe.exceptions.ValidationError: Si quota atteint ou non défini.
    """
    try:
        role_quotas = {
            "SMS User": 100,
            "SMS Manager": 500,
            "System Manager": 9999,
        }

        user_roles = frappe.get_roles(user)
        max_quota = 0

        for role in user_roles:
            if role in role_quotas:
                max_quota = max(max_quota, role_quotas[role])

        if max_quota == 0:
            frappe.throw(_("Aucun quota SMS défini pour cet utilisateur"))

        sent_today = 0

        if frappe.db.exists("DocType", "SMS Campaign Log"):
            try:
                today = datetime.now().date()
                sent_today = frappe.db.count(
                    "SMS Campaign Log",
                    {"sender": user, "date": today, "status": "Sent"},
                )
            except Exception as log_error:
                frappe.log_error(
                    f"Erreur comptage SMS Campaign Log: {log_error}",
                    "SMS Quota Warning",
                )
                sent_today = 0

        if sent_today >= max_quota:
            frappe.throw(
                _("Quota SMS journalier atteint ({0}/{1})").format(
                    sent_today, max_quota
                )
            )

        return max_quota - sent_today

    except frappe.exceptions.ValidationError:
        raise
    except Exception as e:
        frappe.log_error(f"Erreur vérification quota SMS: {e}", "SMS Quota Error")
        frappe.throw(_("Impossible de vérifier le quota SMS: {0}").format(str(e)))


@frappe.whitelist()
def get_user_sms_quota() -> dict[str, Any]:
    """API pour récupérer le quota SMS utilisateur.

    Returns:
        dict[str, Any]: Résultat avec success et remaining_quota.
    """
    try:
        remaining = check_user_sms_quota(frappe.session.user)
        return {"success": True, "remaining_quota": remaining}
    except Exception as e:
        return {"success": False, "message": str(e)}

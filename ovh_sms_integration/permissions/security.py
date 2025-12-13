# -*- coding: utf-8 -*-
"""Security setup and campaign limits for SMS.

Ce module gère la configuration de sécurité et les limites des campagnes.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import frappe
from frappe import _

if TYPE_CHECKING:
    from frappe.model.document import Document


def setup_campaign_security() -> None:
    """Configure la sécurité des campagnes SMS."""
    create_sms_roles()
    setup_default_permissions()
    setup_security_limits()


def create_sms_roles() -> None:
    """Crée les rôles SMS nécessaires."""
    roles_to_create = [
        {
            "role_name": "Campaign Manager",
            "desk_access": 1,
            "description": "Peut créer et gérer les campagnes SMS de marketing",
        },
        {
            "role_name": "SMS Operator",
            "desk_access": 1,
            "description": "Peut exécuter les campagnes SMS mais pas les modifier",
        },
        {
            "role_name": "SMS Viewer",
            "desk_access": 1,
            "description": "Peut consulter les rapports SMS en lecture seule",
        },
    ]

    for role_data in roles_to_create:
        if not frappe.db.exists("Role", role_data["role_name"]):
            role_doc = frappe.get_doc(
                {
                    "doctype": "Role",
                    "role_name": role_data["role_name"],
                    "desk_access": role_data["desk_access"],
                    "description": role_data["description"],
                }
            )
            role_doc.insert()
            frappe.logger().info(f"Rôle créé: {role_data['role_name']}")


def setup_default_permissions() -> None:
    """Configure les permissions par défaut pour les campagnes."""
    permissions_config = {
        "SMS Pricing Campaign": [
            {
                "role": "System Manager",
                "read": 1,
                "write": 1,
                "create": 1,
                "delete": 1,
                "submit": 1,
            },
            {"role": "SMS Manager", "read": 1, "write": 1, "create": 1, "submit": 1},
            {
                "role": "Campaign Manager",
                "read": 1,
                "write": 1,
                "create": 1,
                "submit": 1,
            },
            {"role": "SMS User", "read": 1, "write": 1, "create": 1},
            {"role": "SMS Operator", "read": 1, "submit": 1},
            {"role": "SMS Viewer", "read": 1},
        ],
        "SMS Pricing Item": [
            {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
            {"role": "SMS Manager", "read": 1, "write": 1, "create": 1},
            {"role": "Campaign Manager", "read": 1, "write": 1, "create": 1},
            {"role": "SMS User", "read": 1, "write": 1, "create": 1},
            {"role": "SMS Viewer", "read": 1},
        ],
    }

    for doctype, perms in permissions_config.items():
        _setup_doctype_permissions(doctype, perms)


def _setup_doctype_permissions(
    doctype: str, permissions: list[dict[str, Any]]
) -> None:
    """Configure les permissions pour un DocType spécifique."""
    try:
        for perm in permissions:
            existing = frappe.db.exists(
                "DocPerm", {"parent": doctype, "role": perm["role"]}
            )

            if not existing:
                perm_doc = frappe.get_doc(
                    {
                        "doctype": "DocPerm",
                        "parent": doctype,
                        "parenttype": "DocType",
                        "parentfield": "permissions",
                        "role": perm["role"],
                        "read": perm.get("read", 0),
                        "write": perm.get("write", 0),
                        "create": perm.get("create", 0),
                        "delete": perm.get("delete", 0),
                        "submit": perm.get("submit", 0),
                        "cancel": perm.get("cancel", 0),
                        "amend": perm.get("amend", 0),
                    }
                )
                perm_doc.insert()
                frappe.logger().info(f"Permission créée: {doctype} - {perm['role']}")

    except Exception as e:
        frappe.log_error(f"Erreur setup permissions {doctype}: {e}")


def setup_security_limits() -> None:
    """Configure les limites de sécurité."""
    security_settings = {
        "max_sms_per_campaign": 10000,
        "max_campaigns_per_user_per_day": 5,
        "max_concurrent_campaigns": 3,
        "require_approval_above_amount": 5000,
        "require_approval_above_sms_count": 1000,
    }

    for key, value in security_settings.items():
        frappe.db.set_value(
            "System Settings", "System Settings", f"sms_{key}", value
        )


def validate_campaign_limits(doc: "Document", method: str) -> None:
    """Valide les limites de sécurité pour une campagne.

    Args:
        doc: Document SMS Pricing Campaign à valider.
        method: Nom de la méthode.
    """
    if frappe.flags.in_install or frappe.flags.in_migrate:
        return

    max_sms = (
        frappe.db.get_single_value("System Settings", "sms_max_sms_per_campaign")
        or 10000
    )
    if doc.total_customers > max_sms:
        frappe.throw(
            _("Limite dépassée: maximum {0} SMS par campagne").format(max_sms)
        )

    max_amount = (
        frappe.db.get_single_value(
            "System Settings", "sms_require_approval_above_amount"
        )
        or 5000
    )
    if doc.estimated_revenue > max_amount:
        doc.requires_approval = 1

    max_sms_approval = (
        frappe.db.get_single_value(
            "System Settings", "sms_require_approval_above_sms_count"
        )
        or 1000
    )
    if doc.total_customers > max_sms_approval:
        doc.requires_approval = 1


def check_concurrent_campaigns(user: str | None = None) -> None:
    """Vérifie le nombre de campagnes simultanées.

    Args:
        user: Nom d'utilisateur optionnel.
    """
    if not user:
        user = frappe.session.user

    max_concurrent = (
        frappe.db.get_single_value("System Settings", "sms_max_concurrent_campaigns")
        or 3
    )

    active_campaigns = frappe.db.count(
        "SMS Pricing Campaign",
        {"owner": user, "status": ["in", ["Prêt", "En cours"]], "docstatus": 1},
    )

    if active_campaigns >= max_concurrent:
        frappe.throw(
            _("Limite atteinte: maximum {0} campagnes simultanées").format(
                max_concurrent
            )
        )


@frappe.whitelist()
def request_campaign_approval(
    campaign_name: str, reason: str = ""
) -> dict[str, Any]:
    """Demande d'approbation pour une campagne.

    Args:
        campaign_name: Nom de la campagne nécessitant approbation.
        reason: Raison optionnelle de la demande.

    Returns:
        dict[str, Any]: Résultat avec success, message, approval_id.
    """
    from ovh_sms_integration.permissions.query import has_campaign_permission
    from ovh_sms_integration.permissions.activity import notify_approvers

    try:
        campaign = frappe.get_doc("SMS Pricing Campaign", campaign_name)

        if not has_campaign_permission(campaign):
            frappe.throw(_("Permission insuffisante"))

        approval_request = frappe.get_doc(
            {
                "doctype": "SMS Campaign Approval",
                "campaign": campaign_name,
                "requested_by": frappe.session.user,
                "reason": reason,
                "estimated_cost": campaign.total_sms_cost,
                "sms_count": campaign.total_customers,
                "status": "Pending",
            }
        )
        approval_request.insert()

        notify_approvers(approval_request)

        return {
            "success": True,
            "message": _("Demande d'approbation envoyée"),
            "approval_id": approval_request.name,
        }

    except Exception as e:
        frappe.log_error(f"Erreur demande approbation: {e}")
        return {"success": False, "message": str(e)}

# -*- coding: utf-8 -*-
"""Activity logging for SMS campaigns.

Ce module gère le logging des activités et les notifications.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import frappe

if TYPE_CHECKING:
    from frappe.model.document import Document


def log_sms_activity(campaign: str, action: str, details: str = "") -> None:
    """Log les activités SMS pour audit.

    Args:
        campaign: Nom de la campagne.
        action: Type d'action effectuée.
        details: Détails optionnels de l'action.
    """
    try:
        log_entry = frappe.get_doc(
            {
                "doctype": "SMS Campaign Log",
                "campaign": campaign,
                "user": frappe.session.user,
                "action": action,
                "details": details,
                "timestamp": frappe.utils.now(),
                "ip_address": (
                    frappe.local.request.environ.get("REMOTE_ADDR")
                    if frappe.local.request
                    else None
                ),
            }
        )
        log_entry.insert(ignore_permissions=True)

    except Exception as e:
        frappe.log_error(f"Erreur log activité SMS: {e}")


def notify_approvers(approval_request: "Document") -> None:
    """Notifie les approbateurs d'une demande.

    Args:
        approval_request: Document SMS Campaign Approval à notifier.
    """
    try:
        manager_roles = frappe.get_all(
            "Has Role",
            filters={
                "role": ["in", ["SMS Manager", "System Manager"]],
                "parenttype": "User",
            },
            fields=["parent"],
            distinct=True,
        )

        if not manager_roles:
            return

        approvers = []
        for role_assignment in manager_roles:
            user = frappe.get_doc("User", role_assignment.parent)
            if user.enabled and user.email:
                approvers.append({"email": user.email, "full_name": user.full_name})

        if not approvers:
            return

        subject = f"Demande d'approbation campagne SMS: {approval_request.campaign}"
        message = frappe.render_template(
            "ovh_sms_integration/templates/emails/campaign_approval_request.html",
            {
                "campaign": approval_request.campaign,
                "requested_by": approval_request.requested_by,
                "sms_count": approval_request.sms_count,
                "estimated_cost": approval_request.estimated_cost,
                "reason": approval_request.reason,
                "approval_link": (
                    f"/app/sms-campaign-approval/{approval_request.name}"
                ),
            },
        )

        recipients = [approver["email"] for approver in approvers]

        frappe.sendmail(
            recipients=recipients,
            subject=subject,
            message=message,
            header=["Demande d'approbation SMS", "orange"],
        )

    except Exception as e:
        frappe.log_error(f"Erreur notification approbateurs: {e}")

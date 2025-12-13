# -*- coding: utf-8 -*-
"""GDPR compliance functions for SMS campaigns.

Ce module gère la conformité RGPD et l'anonymisation des données.
"""
from __future__ import annotations

from typing import Any

import frappe
from frappe import _


@frappe.whitelist()
def validate_phone_consent(
    phone_number: str, campaign_type: str = "marketing"
) -> dict[str, Any]:
    """Vérifie le consentement RGPD pour un numéro de téléphone.

    Args:
        phone_number: Numéro de téléphone à vérifier.
        campaign_type: Type de campagne.

    Returns:
        dict[str, Any]: Résultat avec success et message.
    """
    try:
        customers = frappe.get_all(
            "Customer",
            filters={"mobile_no": phone_number},
            fields=["name", "sms_opt_out"],
            limit=1,
        )

        if not customers:
            customers = frappe.get_all(
                "Customer",
                filters={"phone": phone_number},
                fields=["name", "sms_opt_out"],
                limit=1,
            )

        if customers:
            customer = customers[0]
            if customer.sms_opt_out:
                return {
                    "success": False,
                    "message": _("Client a refusé les SMS marketing"),
                }

        blocked = frappe.db.exists("SMS Blacklist", {"phone_number": phone_number})
        if blocked:
            return {"success": False, "message": _("Numéro dans la liste de blocage")}

        return {"success": True, "message": _("Consentement validé")}

    except Exception as e:
        frappe.log_error(f"Erreur validation consentement: {e}")
        return {"success": False, "message": _("Erreur validation consentement")}


def enforce_gdpr_compliance() -> None:
    """Applique la conformité RGPD.

    Anonymise les campagnes de plus de 3 ans (1095 jours).
    """
    try:
        retention_days = (
            frappe.db.get_single_value("System Settings", "sms_data_retention_days")
            or 1095
        )
        cutoff_date = frappe.utils.add_days(frappe.utils.today(), -retention_days)

        old_campaigns = frappe.get_all(
            "SMS Pricing Campaign",
            filters={"creation": ["<", cutoff_date], "anonymized": ["!=", 1]},
            pluck="name",
        )

        for campaign_name in old_campaigns:
            anonymize_campaign_data(campaign_name)

    except Exception as e:
        frappe.log_error(f"Erreur conformité RGPD: {e}")


def anonymize_campaign_data(campaign_name: str) -> None:
    """Anonymise les données d'une campagne.

    Args:
        campaign_name: Nom de la campagne à anonymiser.
    """
    try:
        campaign = frappe.get_doc("SMS Pricing Campaign", campaign_name)

        for item in campaign.pricing_items:
            item.customer_mobile = "***ANONYMIZED***"
            item.customer_name = "Client Anonyme"

        campaign.anonymized = 1
        campaign.save(ignore_permissions=True)

        frappe.logger().info(f"Campagne anonymisée: {campaign_name}")

    except Exception as e:
        frappe.log_error(f"Erreur anonymisation campagne {campaign_name}: {e}")

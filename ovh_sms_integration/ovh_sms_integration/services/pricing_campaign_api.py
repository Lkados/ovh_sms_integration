# -*- coding: utf-8 -*-
"""API endpoints for SMS Pricing Campaign.

Ce module contient les fonctions whitelistées pour les campagnes de tarification.
"""
from __future__ import annotations

from typing import Any

import frappe
from frappe import _


@frappe.whitelist()
def send_all_campaign_sms(campaign_name: str) -> dict[str, Any]:
    """API endpoint pour envoyer tous les SMS d'une campagne.

    Args:
        campaign_name: Nom/ID de la campagne.

    Returns:
        dict[str, Any]: Résultats avec success, message, sent, failed, details.
    """
    try:
        campaign = frappe.get_doc("SMS Pricing Campaign", campaign_name)

        if campaign.docstatus != 1:
            return {
                "success": False,
                "message": _("La campagne doit être soumise avant l'envoi"),
            }

        results = campaign.send_all_sms()

        return {
            "success": True,
            "message": _("{0} SMS envoyés, {1} échecs").format(
                results["sent"], results["failed"]
            ),
            "results": results,
        }

    except Exception as e:
        frappe.log_error(f"Erreur API envoi campagne: {e}")
        return {"success": False, "message": _("Erreur: {0}").format(str(e))}


@frappe.whitelist()
def send_selected_campaign_sms(campaign_name: str) -> dict[str, Any]:
    """API endpoint pour envoyer uniquement les SMS sélectionnés.

    Args:
        campaign_name: Nom/ID de la campagne.

    Returns:
        dict[str, Any]: Résultat avec success, message et results.
    """
    try:
        campaign = frappe.get_doc("SMS Pricing Campaign", campaign_name)

        selected_count = sum(
            1
            for item in campaign.pricing_items
            if item.selected_for_sending and not item.sms_sent
        )

        if selected_count == 0:
            return {
                "success": False,
                "message": _("Aucun élément sélectionné pour l'envoi"),
            }

        results = campaign.send_all_sms()

        return {
            "success": True,
            "message": _("{0} SMS envoyés sur {1} sélectionnés").format(
                results["sent"], selected_count
            ),
            "results": results,
        }

    except Exception as e:
        frappe.log_error(f"Erreur API envoi sélectionnés: {e}")
        return {"success": False, "message": _("Erreur: {0}").format(str(e))}


@frappe.whitelist()
def preview_campaign_messages(campaign_name: str) -> dict[str, Any]:
    """API endpoint pour prévisualiser les messages SMS.

    Args:
        campaign_name: Nom/ID de la campagne.

    Returns:
        dict[str, Any]: Résultat avec success et previews (liste).
    """
    try:
        campaign = frappe.get_doc("SMS Pricing Campaign", campaign_name)
        previews = campaign.get_preview_messages()

        return {"success": True, "previews": previews}

    except Exception as e:
        frappe.log_error(f"Erreur API aperçu: {e}")
        return {"success": False, "message": _("Erreur: {0}").format(str(e))}


@frappe.whitelist()
def send_campaign_test_sms(campaign_name: str, test_mobile: str) -> dict[str, Any]:
    """API endpoint pour envoyer un SMS de test.

    Args:
        campaign_name: Nom/ID de la campagne.
        test_mobile: Numéro de test pour recevoir le SMS.

    Returns:
        dict[str, Any]: Résultat avec success, message, content, etc.
    """
    import copy

    try:
        campaign = frappe.get_doc("SMS Pricing Campaign", campaign_name)

        if not campaign.pricing_items:
            return {"success": False, "message": _("Aucun article dans la campagne")}

        test_item = campaign.pricing_items[0]
        test_item_copy = copy.deepcopy(test_item)
        test_item_copy.customer_name = "Client Test"
        test_item_copy.customer_mobile = test_mobile

        message = campaign.format_sms_message(test_item_copy)

        sms_settings = frappe.get_single("OVH SMS Settings")
        if not sms_settings.enabled:
            return {"success": False, "message": _("OVH SMS non activé")}

        result = sms_settings.send_sms(message, test_mobile)

        if result and result.get("success"):
            return {
                "success": True,
                "message": _("SMS de test envoyé vers {0}").format(test_mobile),
                "content": message,
                "valuation_rate": test_item.valuation_rate,
                "margin_eur": test_item.margin_amount_eur,
                "final_price": test_item.final_price,
            }
        else:
            return {
                "success": False,
                "message": (
                    result.get("message", "Erreur envoi SMS")
                    if result
                    else "Pas de réponse"
                ),
            }

    except Exception as e:
        frappe.log_error(f"Erreur API test SMS: {e}")
        return {"success": False, "message": _("Erreur: {0}").format(str(e))}


@frappe.whitelist()
def get_item_valuation_rate(item_code: str) -> dict[str, Any]:
    """API endpoint pour récupérer le taux de valorisation d'un article.

    Args:
        item_code: Code de l'article.

    Returns:
        dict[str, Any]: Résultat avec success, rate et source.
    """
    try:
        # Méthode 1: Dernière valorisation en stock
        valuation = frappe.get_all(
            "Stock Ledger Entry",
            filters={"item_code": item_code, "valuation_rate": [">", 0]},
            fields=["valuation_rate"],
            order_by="posting_date desc, posting_time desc",
            limit=1,
        )

        if valuation:
            return {
                "success": True,
                "rate": valuation[0].valuation_rate,
                "source": "Stock Ledger Entry",
            }

        # Méthode 2: Prix standard de l'article
        item_doc = frappe.get_doc("Item", item_code)
        if hasattr(item_doc, "standard_rate") and item_doc.standard_rate:
            return {
                "success": True,
                "rate": item_doc.standard_rate,
                "source": "Standard Rate",
            }

        # Méthode 3: Dernier prix d'achat
        purchase_price = frappe.get_all(
            "Purchase Invoice Item",
            filters={"item_code": item_code, "rate": [">", 0]},
            fields=["rate"],
            order_by="creation desc",
            limit=1,
        )

        if purchase_price:
            return {
                "success": True,
                "rate": purchase_price[0].rate,
                "source": "Purchase Invoice",
            }

        return {"success": True, "rate": 0, "source": "No data found"}

    except Exception as e:
        frappe.log_error(f"Erreur API taux valorisation: {e}")
        return {"success": False, "message": _("Erreur: {0}").format(str(e))}


@frappe.whitelist()
def get_customer_mobile_for_campaign(customer: str) -> dict[str, Any]:
    """API endpoint pour récupérer le mobile d'un client.

    Args:
        customer: Nom/ID du client.

    Returns:
        dict[str, Any]: Résultat avec success et mobile.
    """
    from ovh_sms_integration.utils.phone import get_customer_mobile_number

    try:
        customer_doc = frappe.get_doc("Customer", customer)
        mobile = get_customer_mobile_number(customer_doc)

        return {"success": True, "mobile": mobile}

    except Exception as e:
        frappe.log_error(f"Erreur API mobile client: {e}")
        return {"success": False, "message": _("Erreur: {0}").format(str(e))}


def calculate_campaign_roi(campaign_name: str) -> dict[str, float] | None:
    """Calcule le ROI d'une campagne SMS.

    Args:
        campaign_name: Nom/ID de la campagne.

    Returns:
        dict[str, float] | None: ROI avec roi_percent, revenue, cost, profit.
    """
    try:
        campaign = frappe.get_doc("SMS Pricing Campaign", campaign_name)

        sms_cost = campaign.total_sms_cost or 0
        revenue = campaign.estimated_revenue or 0

        if sms_cost > 0:
            roi = ((revenue - sms_cost) / sms_cost) * 100
        else:
            roi = 0

        return {
            "roi_percent": roi,
            "revenue": revenue,
            "cost": sms_cost,
            "profit": revenue - sms_cost,
        }

    except Exception as e:
        frappe.log_error(f"Erreur calcul ROI: {e}")
        return None

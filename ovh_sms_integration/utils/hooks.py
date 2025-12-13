# -*- coding: utf-8 -*-
"""Document hooks for OVH SMS Integration.

Ce module gère les hooks sur les documents Frappe pour l'envoi automatique de SMS.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
from frappe import _

if TYPE_CHECKING:
    from frappe.model.document import Document


def on_document_update(doc: "Document", method: str | None = None) -> None:
    """Hook appelé lors de la mise à jour d'un document.

    Vérifie si des SMS doivent être envoyés suite à la mise à jour.

    Args:
        doc: Document mis à jour.
        method: Nom de la méthode déclencheur (optionnel).
    """
    # Placeholder - implémentation spécifique selon le doctype
    pass


def on_document_submit(doc: "Document", method: str | None = None) -> None:
    """Hook appelé lors de la soumission d'un document.

    Args:
        doc: Document soumis.
        method: Nom de la méthode déclencheur (optionnel).
    """
    doctype_handlers = {
        "Sales Order": send_sales_order_sms,
        "Payment Entry": send_payment_confirmation_sms,
        "Delivery Note": send_delivery_sms,
        "Purchase Order": send_purchase_order_sms,
    }

    handler = doctype_handlers.get(doc.doctype)
    if handler:
        handler(doc, method)


def on_document_cancel(doc: "Document", method: str | None = None) -> None:
    """Hook appelé lors de l'annulation d'un document.

    Args:
        doc: Document annulé.
        method: Nom de la méthode déclencheur (optionnel).
    """
    # Placeholder pour notification d'annulation si nécessaire
    pass


def send_sales_order_sms(doc: "Document", method: str | None = None) -> None:
    """Envoie un SMS de confirmation de commande client.

    Args:
        doc: Document Sales Order.
        method: Nom de la méthode déclencheur (optionnel).

    Note:
        Le SMS n'est envoyé que si:
        - L'intégration OVH SMS est activée
        - Le client a un numéro mobile
        - Un template de message est configuré
    """
    from ovh_sms_integration.utils.phone import get_contact_mobile
    from ovh_sms_integration.utils.core import get_ovh_sms_settings, send_sms

    settings = get_ovh_sms_settings()
    if not settings:
        return

    # Récupérer le mobile du client
    customer = frappe.get_doc("Customer", doc.customer)
    mobile = get_contact_mobile(customer)

    if not mobile:
        return

    # Template de confirmation de commande
    template = _(
        "Bonjour {{customer_name}}, votre commande {{name}} "
        "d'un montant de {{grand_total}} € a été confirmée."
    )

    context = {
        "customer_name": doc.customer_name,
        "name": doc.name,
        "grand_total": f"{doc.grand_total:.2f}",
    }

    send_sms(template, mobile, context=context)


def send_payment_confirmation_sms(doc: "Document", method: str | None = None) -> None:
    """Envoie un SMS de confirmation de paiement.

    Args:
        doc: Document Payment Entry.
        method: Nom de la méthode déclencheur (optionnel).
    """
    from ovh_sms_integration.utils.phone import get_contact_mobile
    from ovh_sms_integration.utils.core import get_ovh_sms_settings, send_sms

    settings = get_ovh_sms_settings()
    if not settings:
        return

    # Vérifier si c'est un paiement client (Receive)
    if doc.payment_type != "Receive":
        return

    # Récupérer le mobile du client
    if not doc.party or doc.party_type != "Customer":
        return

    customer = frappe.get_doc("Customer", doc.party)
    mobile = get_contact_mobile(customer)

    if not mobile:
        return

    template = _(
        "Bonjour {{party_name}}, nous confirmons la réception "
        "de votre paiement de {{paid_amount}} €. Merci!"
    )

    context = {
        "party_name": doc.party_name,
        "paid_amount": f"{doc.paid_amount:.2f}",
    }

    send_sms(template, mobile, context=context)


def send_delivery_sms(doc: "Document", method: str | None = None) -> None:
    """Envoie un SMS de notification de livraison.

    Args:
        doc: Document Delivery Note.
        method: Nom de la méthode déclencheur (optionnel).
    """
    from ovh_sms_integration.utils.phone import get_contact_mobile
    from ovh_sms_integration.utils.core import get_ovh_sms_settings, send_sms

    settings = get_ovh_sms_settings()
    if not settings:
        return

    customer = frappe.get_doc("Customer", doc.customer)
    mobile = get_contact_mobile(customer)

    if not mobile:
        return

    template = _(
        "Bonjour {{customer_name}}, votre livraison {{name}} "
        "est en cours de préparation."
    )

    context = {
        "customer_name": doc.customer_name,
        "name": doc.name,
    }

    send_sms(template, mobile, context=context)


def send_purchase_order_sms(doc: "Document", method: str | None = None) -> None:
    """Envoie un SMS de notification de commande fournisseur.

    Args:
        doc: Document Purchase Order.
        method: Nom de la méthode déclencheur (optionnel).
    """
    from ovh_sms_integration.utils.phone import get_contact_mobile
    from ovh_sms_integration.utils.core import get_ovh_sms_settings, send_sms

    settings = get_ovh_sms_settings()
    if not settings:
        return

    supplier = frappe.get_doc("Supplier", doc.supplier)
    mobile = get_contact_mobile(supplier)

    if not mobile:
        return

    template = _(
        "Nouvelle commande {{name}} pour {{supplier_name}}. "
        "Montant: {{grand_total}} €"
    )

    context = {
        "name": doc.name,
        "supplier_name": doc.supplier_name,
        "grand_total": f"{doc.grand_total:.2f}",
    }

    send_sms(template, mobile, context=context)

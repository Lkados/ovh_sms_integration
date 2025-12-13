# -*- coding: utf-8 -*-
"""Phone number utilities for OVH SMS Integration.

Ce module gère la validation et le formatage des numéros de téléphone.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

import frappe
from frappe import _

if TYPE_CHECKING:
    from frappe.model.document import Document


def validate_phone_number(phone: str | None) -> str:
    """Valide et normalise un numéro de téléphone au format international.

    Nettoie le numéro des caractères non numériques et le convertit
    au format international français (+33...).

    Args:
        phone: Numéro de téléphone brut.
            Formats acceptés: "0612345678", "06 12 34 56 78",
            "+33612345678", "06.12.34.56.78".

    Returns:
        str: Numéro normalisé au format international (+33612345678).

    Raises:
        ValueError: Si phone est vide, None ou invalide.

    Example:
        >>> validate_phone_number("06 12 34 56 78")
        '+33612345678'
        >>> validate_phone_number("+33612345678")
        '+33612345678'
        >>> validate_phone_number("")  # raises ValueError
    """
    if not phone:
        raise ValueError(_("Numéro de téléphone vide"))

    # Nettoyage du numéro (garde seulement chiffres et +)
    cleaned_phone: str = re.sub(r"[^\d+]", "", str(phone))

    # Conversion au format international français
    if cleaned_phone.startswith("0"):
        cleaned_phone = "+33" + cleaned_phone[1:]
    elif not cleaned_phone.startswith("+"):
        cleaned_phone = "+33" + cleaned_phone

    # Validation du format final
    if not re.match(r"^\+\d{10,15}$", cleaned_phone):
        raise ValueError(_("Numéro de téléphone invalide: {0}").format(phone))

    return cleaned_phone


def get_contact_mobile(doc: "Document") -> str | None:
    """Extrait le numéro mobile d'un document ou de ses contacts liés.

    Recherche le numéro mobile dans l'ordre suivant:
    1. Champ mobile_no du document
    2. Champ cell_number du document
    3. Contacts liés via Dynamic Link

    Args:
        doc: Document Frappe (Customer, Supplier, etc.).

    Returns:
        str | None: Numéro mobile normalisé, ou None si non trouvé.

    Example:
        >>> customer = frappe.get_doc("Customer", "CUST-001")
        >>> mobile = get_contact_mobile(customer)
        >>> if mobile:
        ...     send_sms("Hello", mobile)
    """
    # Vérifier d'abord le champ mobile_no du document
    if hasattr(doc, "mobile_no") and doc.mobile_no:
        try:
            return validate_phone_number(doc.mobile_no)
        except ValueError:
            pass

    # Vérifier cell_number (utilisé sur Employee)
    if hasattr(doc, "cell_number") and doc.cell_number:
        try:
            return validate_phone_number(doc.cell_number)
        except ValueError:
            pass

    # Chercher dans les contacts liés
    try:
        contacts = frappe.get_all(
            "Dynamic Link",
            filters={
                "link_doctype": doc.doctype,
                "link_name": doc.name,
                "parenttype": "Contact",
            },
            fields=["parent"],
        )

        for contact in contacts:
            contact_doc = frappe.get_doc("Contact", contact.parent)
            if contact_doc.mobile_no:
                try:
                    return validate_phone_number(contact_doc.mobile_no)
                except ValueError:
                    continue

    except Exception as e:
        frappe.log_error(f"Erreur récupération contact mobile: {e}")

    return None


def get_customer_mobile_number(customer: "Document") -> str | None:
    """Récupère le numéro mobile d'un client.

    Args:
        customer: Document Customer.

    Returns:
        str | None: Numéro mobile normalisé, ou None si non trouvé.

    Note:
        Délègue à get_contact_mobile() pour la logique de recherche.
    """
    return get_contact_mobile(customer)


def get_employee_mobile_number(employee: "Document") -> str | None:
    """Récupère le numéro mobile d'un employé.

    Vérifie les champs dans l'ordre:
    1. cell_number
    2. personal_mobile
    3. company_phone

    Args:
        employee: Document Employee.

    Returns:
        str | None: Numéro mobile normalisé, ou None si non trouvé.
    """
    # Champs prioritaires pour Employee
    mobile_fields = ["cell_number", "personal_mobile", "company_phone"]

    for field in mobile_fields:
        if hasattr(employee, field) and getattr(employee, field):
            try:
                return validate_phone_number(getattr(employee, field))
            except ValueError:
                continue

    return None

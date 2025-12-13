# -*- coding: utf-8 -*-
"""Template utilities for OVH SMS Integration.

Ce module gère le formatage des messages SMS avec Jinja2.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import frappe
from frappe import _
from jinja2 import Template

if TYPE_CHECKING:
    from frappe.model.document import Document


def format_message_template(template: str, context: dict[str, Any]) -> str:
    """Formate un template de message SMS avec Jinja2.

    Rend un template Jinja2 avec les variables fournies dans le contexte.
    Convertit automatiquement les dates et objets en chaînes de caractères.

    Args:
        template: Template Jinja2 du message.
            Example: "Bonjour {{name}}, votre RDV est le {{date}}"
        context: Dictionnaire de variables pour le template.
            Example: {"name": "Jean", "date": "15/01/2025"}

    Returns:
        str: Message formaté avec les variables substituées.
            Retourne le template original en cas d'erreur.

    Example:
        >>> template = "Bonjour {{name}}, montant: {{amount}}€"
        >>> context = {"name": "Marie", "amount": 150.50}
        >>> format_message_template(template, context)
        'Bonjour Marie, montant: 150.5€'
    """
    if not template or not context:
        return template

    try:
        # Conversion des valeurs en types sûrs
        safe_context: dict[str, str | int | float] = {}
        for key, value in context.items():
            if isinstance(value, (str, int, float)):
                safe_context[key] = value
            elif hasattr(value, "strftime"):
                safe_context[key] = value.strftime("%d/%m/%Y %H:%M")
            else:
                safe_context[key] = str(value)

        template_obj: Template = Template(template)
        return template_obj.render(**safe_context)
    except Exception as e:
        frappe.log_error(f"Erreur formatage template SMS: {e}")
        return template


def format_event_reminder_message(
    event: dict[str, Any],
    customer_name: str,
    template: str | None = None,
) -> str:
    """Formate un message de rappel d'événement.

    Args:
        event: Dictionnaire contenant les infos de l'événement.
            Champs attendus: subject, starts_on, description.
        customer_name: Nom du client destinataire.
        template: Template Jinja2 personnalisé (optionnel).
            Si None, utilise le template par défaut.

    Returns:
        str: Message de rappel formaté.

    Example:
        >>> event = {"subject": "Entretien", "starts_on": datetime.now()}
        >>> format_event_reminder_message(event, "ACME Corp")
        'Bonjour ACME Corp, rappel: Entretien le 15/01/2025 à 14:30'
    """
    if not template:
        template = _(
            "Bonjour {{customer_name}}, rappel: {{event_subject}} "
            "le {{event_date}} à {{event_time}}"
        )

    starts_on = event.get("starts_on")
    if starts_on:
        if isinstance(starts_on, str):
            from datetime import datetime

            starts_on = datetime.fromisoformat(starts_on)
        event_date = starts_on.strftime("%d/%m/%Y")
        event_time = starts_on.strftime("%H:%M")
    else:
        event_date = _("Non défini")
        event_time = ""

    context = {
        "customer_name": customer_name,
        "event_subject": event.get("subject", ""),
        "event_date": event_date,
        "event_time": event_time,
        "event_description": event.get("description", "")[:100],
    }

    return format_message_template(template, context)


def format_sms_message(template: str, doc: "Document") -> str:
    """Formate un message SMS à partir d'un document Frappe.

    Extrait automatiquement les champs du document pour le contexte.

    Args:
        template: Template Jinja2 du message.
        doc: Document Frappe source des données.

    Returns:
        str: Message formaté.

    Example:
        >>> so = frappe.get_doc("Sales Order", "SO-001")
        >>> template = "Commande {{name}} pour {{customer}}"
        >>> format_sms_message(template, so)
        'Commande SO-001 pour ACME Corp'
    """
    context = doc.as_dict()
    return format_message_template(template, context)

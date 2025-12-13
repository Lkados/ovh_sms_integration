# -*- coding: utf-8 -*-
"""Event data parsing utilities for OVH SMS Integration.

Ce module gère l'extraction de données structurées depuis les descriptions d'événements.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import frappe

if TYPE_CHECKING:
    from ovh_sms_integration.types import ParsedEventData


def parse_event_data(description: str | None) -> "ParsedEventData":
    """Parse toutes les données structurées de l'événement.

    Extrait les informations structurées depuis la description markdown
    de l'événement en utilisant des regex.

    Args:
        description: Description de l'événement (peut contenir du markdown).

    Returns:
        ParsedEventData: Dictionnaire avec les champs extraits:
            - client: Nom du client
            - reference: Numéro de référence
            - type: Type d'événement
            - article: Article/produit
            - tel_client: Téléphone client
            - email_client: Email client
            - appareil: Équipement/appareil
            - camion_requis: Si camion requis (Oui/Non)

    Example:
        >>> desc = "**Client:** John\\n**Type:** Entretien"
        >>> data = parse_event_data(desc)
        >>> data["client"]
        'John'

    Note:
        - Essaie d'abord avec markdown (**Key:**)
        - Fallback sans markdown (Key:)
        - Retourne {} si description vide ou erreur
        - Les erreurs sont loggées mais ne lèvent pas d'exception
    """
    if not description:
        return {}

    try:
        data: dict[str, Any] = {}

        # Patterns pour extraire les informations (avec markdown)
        patterns = {
            "client": r"\*\*Client:\*\*\s*([^\n\r*]+)",
            "reference": r"\*\*Référence:\*\*\s*([^\n\r*]+)",
            "type": r"\*\*Type:\*\*\s*([^\n\r*]+)",
            "article": r"\*\*Article:\*\*\s*([^\n\r*]+)",
            "tel_client": r"\*\*Tél client:\*\*\s*([^\n\r*]+)",
            "email_client": r"\*\*Email client:\*\*\s*([^\n\r*]+)",
            "appareil": r"\*\*Appareil:\*\*\s*([^\n\r*]+)",
            "camion_requis": r"\*\*Camion requis:\*\*\s*([^\n\r*]+)",
        }

        # Extraction avec markdown
        for key, pattern in patterns.items():
            match = re.search(pattern, description)
            if match:
                data[key] = match.group(1).strip()

        # Si pas trouvé avec markdown, essayer sans
        if not data:
            patterns_simple = {
                "client": r"Client:\s*([^\n\r]+)",
                "reference": r"Référence:\s*([^\n\r]+)",
                "type": r"Type:\s*([^\n\r]+)",
                "article": r"Article:\s*([^\n\r]+)",
                "tel_client": r"Tél client:\s*([^\n\r]+)",
                "email_client": r"Email client:\s*([^\n\r]+)",
                "appareil": r"Appareil:\s*([^\n\r]+)",
                "camion_requis": r"Camion requis:\s*([^\n\r]+)",
            }

            for key, pattern in patterns_simple.items():
                match = re.search(pattern, description)
                if match:
                    data[key] = match.group(1).strip()

        return data

    except Exception as e:
        frappe.log_error(f"Erreur parsing données événement: {e}")
        return {}


def extract_event_type(description: str | None) -> str | None:
    """Extrait le type d'événement depuis la description structurée.

    Parse la description pour extraire le champ "Type:" qui indique
    le type d'événement (Entretien, Livraison, etc.).

    Args:
        description: Description de l'événement avec données structurées.

    Returns:
        str | None: Type d'événement extrait, ou None si non trouvé.

    Example:
        >>> desc = "**Type:** Entretien\\n**Client:** John"
        >>> extract_event_type(desc)
        'Entretien'

    Note:
        - Essaie d'abord avec markdown (**Type:**)
        - Fallback sans markdown (Type:)
        - Retourne None si description vide ou type non trouvé
        - Les erreurs sont loggées mais ne lèvent pas d'exception
    """
    if not description:
        return None

    try:
        # Recherche du pattern "Type:" avec markdown
        type_match = re.search(r"\*\*Type:\*\*\s*([^\n\r*]+)", description)
        if type_match:
            return type_match.group(1).strip()

        # Essayer aussi sans les ** (markdown)
        type_match = re.search(r"Type:\s*([^\n\r]+)", description)
        if type_match:
            return type_match.group(1).strip()

        return None
    except Exception as e:
        frappe.log_error(f"Erreur extraction type événement: {e}")
        return None


def build_event_context(
    event_doc: Any,
    customer_name: str | None = None,
    employee_name: str | None = None,
) -> dict[str, Any]:
    """Construit le contexte de template pour un événement.

    Prépare toutes les variables disponibles pour le rendu du template
    de message SMS.

    Args:
        event_doc: Document Event Frappe.
        customer_name: Nom du client destinataire. Par défaut None.
        employee_name: Nom de l'employé destinataire. Par défaut None.

    Returns:
        dict[str, Any]: Contexte avec toutes les variables disponibles:
            - subject, description, event_name
            - start_date, start_time, location
            - customer_name, employee_name
            - duration
            - Données parsées (client, reference, type, etc.)

    Example:
        >>> event = frappe.get_doc("Event", "EVT-001")
        >>> context = build_event_context(event, customer_name="John")
        >>> template.render(**context)
    """
    # Parse des données structurées
    event_data = parse_event_data(event_doc.description)

    # Préparation du contexte de base
    context: dict[str, Any] = {
        "subject": event_doc.subject or "",
        "description": event_doc.description or "",
        "event_name": event_doc.name,
        "start_date": (
            event_doc.starts_on.strftime("%d/%m/%Y") if event_doc.starts_on else ""
        ),
        "start_time": (
            event_doc.starts_on.strftime("%H:%M") if event_doc.starts_on else ""
        ),
        "location": getattr(event_doc, "location", "") or "",
        "customer_name": customer_name or "",
        "employee_name": employee_name or "",
    }

    # Ajout des données parsées
    context.update(
        {
            "client": event_data.get("client", ""),
            "reference": event_data.get("reference", ""),
            "type": event_data.get("type", ""),
            "article": event_data.get("article", ""),
            "tel_client": event_data.get("tel_client", ""),
            "email_client": event_data.get("email_client", ""),
            "appareil": event_data.get("appareil", ""),
            "camion_requis": event_data.get("camion_requis", ""),
        }
    )

    # Calcul de la durée si disponible
    if event_doc.starts_on and event_doc.ends_on:
        duration = (event_doc.ends_on - event_doc.starts_on).total_seconds() / 60
        context["duration"] = int(duration)
    else:
        context["duration"] = ""

    return context

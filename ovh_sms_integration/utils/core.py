# -*- coding: utf-8 -*-
"""Core SMS functions for OVH SMS Integration.

Ce module contient les fonctions principales d'envoi de SMS.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import frappe
from frappe import _

if TYPE_CHECKING:
    from frappe.model.document import Document

    from ovh_sms_integration.types import SMSResult


def get_ovh_sms_settings() -> "Document | None":
    """Récupère les paramètres de configuration OVH SMS.

    Vérifie si l'intégration OVH SMS est activée et retourne
    le document de configuration singleton.

    Returns:
        Document: Instance de 'OVH SMS Settings' si activé.
        None: Si l'intégration est désactivée.

    Example:
        >>> settings = get_ovh_sms_settings()
        >>> if settings:
        ...     result = settings.send_sms("Test", "+33612345678")
    """
    settings: "Document" = frappe.get_single("OVH SMS Settings")
    if not settings.enabled:
        return None
    return settings


def send_sms(
    message: str,
    receiver: str,
    sender: str | None = None,
    context: dict[str, Any] | None = None,
) -> "SMSResult | None":
    """Envoie un SMS via l'intégration OVH.

    Cette fonction principale gère tout le processus d'envoi SMS:
    - Vérification de la configuration OVH
    - Formatage du message avec template Jinja2 si contexte fourni
    - Validation et normalisation du numéro de téléphone
    - Envoi effectif via l'API OVH

    Args:
        message: Contenu du SMS (peut contenir des variables Jinja2).
        receiver: Numéro de téléphone du destinataire.
        sender: Nom de l'expéditeur SMS (optionnel).
        context: Dictionnaire de variables pour le template Jinja2.

    Returns:
        SMSResult: Résultat de l'envoi avec success, message, details.
        None: Si erreur ou intégration désactivée.

    Example:
        >>> result = send_sms(
        ...     message="Bonjour {{name}}",
        ...     receiver="+33612345678",
        ...     context={"name": "Jean"}
        ... )
        >>> if result and result["success"]:
        ...     print("SMS envoyé!")
    """
    from ovh_sms_integration.utils.phone import validate_phone_number
    from ovh_sms_integration.utils.templates import format_message_template

    settings = get_ovh_sms_settings()
    if not settings:
        frappe.log_error(_("OVH SMS non activé"))
        return None

    try:
        # Formatage du message si contexte fourni
        if context:
            message = format_message_template(message, context)

        # Validation du numéro
        validated_phone = validate_phone_number(receiver)

        # Envoi via OVH Settings
        result = settings.send_sms(message, validated_phone, sender)

        return result

    except ValueError as e:
        frappe.log_error(f"Erreur validation numéro: {e}")
        return {"success": False, "message": str(e)}
    except Exception as e:
        frappe.log_error(f"Erreur envoi SMS: {e}")
        return {"success": False, "message": str(e)}


def send_bulk_sms(
    message: str,
    receivers: list[str],
    sender: str | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Envoie un SMS à plusieurs destinataires.

    Args:
        message: Contenu du SMS.
        receivers: Liste de numéros de téléphone.
        sender: Nom de l'expéditeur (optionnel).
        context: Variables pour le template (optionnel).

    Returns:
        dict: Statistiques d'envoi avec sent, failed, details.

    Example:
        >>> result = send_bulk_sms(
        ...     "Promo du jour!",
        ...     ["+33612345678", "+33698765432"]
        ... )
        >>> print(f"Envoyés: {result['sent']}, Échoués: {result['failed']}")
    """
    results = {"sent": 0, "failed": 0, "details": []}

    for receiver in receivers:
        result = send_sms(message, receiver, sender, context)
        if result and result.get("success"):
            results["sent"] += 1
        else:
            results["failed"] += 1
        results["details"].append({"receiver": receiver, "result": result})

    return results

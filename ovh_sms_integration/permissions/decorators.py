# -*- coding: utf-8 -*-
"""Security decorators for SMS functions.

Ce module fournit des décorateurs de sécurité réutilisables.
"""
from __future__ import annotations

from typing import Any, Callable

import frappe
from frappe import _


def require_sms_permission(f: Callable[..., Any]) -> Callable[..., Any]:
    """Décorateur pour exiger les permissions SMS.

    Args:
        f: Fonction à décorer.

    Returns:
        Callable: Fonction décorée avec validation de permissions.

    Example:
        >>> @require_sms_permission
        ... def send_bulk_sms(recipients):
        ...     pass
    """
    from ovh_sms_integration.permissions.query import validate_sms_sending_permission

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        validate_sms_sending_permission()
        return f(*args, **kwargs)

    return wrapper


def log_sms_action(
    action: str,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Décorateur pour logger les actions SMS.

    Args:
        action: Type d'action à logger.

    Returns:
        Callable: Décorateur de fonction.

    Example:
        >>> @log_sms_action("send")
        ... def send_campaign(campaign_name):
        ...     pass
    """
    from ovh_sms_integration.permissions.activity import log_sms_activity

    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = f(*args, **kwargs)
            campaign = kwargs.get("campaign_name") or (args[0] if args else None)
            if campaign:
                log_sms_activity(campaign, action, f"Fonction: {f.__name__}")
            return result

        return wrapper

    return decorator


def rate_limit_sms(
    max_per_minute: int = 10,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Décorateur pour limiter le taux d'envoi SMS.

    Args:
        max_per_minute: Nombre maximum d'appels par minute.

    Returns:
        Callable: Décorateur de fonction.

    Example:
        >>> @rate_limit_sms(max_per_minute=5)
        ... def send_sms(phone, message):
        ...     pass
    """

    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            user = frappe.session.user
            cache_key = f"sms_rate_limit_{user}"

            current_count = frappe.cache().get(cache_key) or 0

            if current_count >= max_per_minute:
                frappe.throw(
                    _("Limite de débit atteinte. Réessayez dans 1 minute.")
                )

            frappe.cache().set(cache_key, current_count + 1, expires_in_sec=60)

            return f(*args, **kwargs)

        return wrapper

    return decorator

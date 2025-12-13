# -*- coding: utf-8 -*-
"""Utils package for OVH SMS Integration.

Ce package contient les utilitaires pour l'envoi de SMS via OVH.

Structure:
- core.py: Fonctions principales (get_ovh_sms_settings, send_sms)
- phone.py: Validation et formatage des numéros
- templates.py: Formatage des messages avec Jinja2
- events.py: Gestion des rappels d'événements
- hooks.py: Hooks sur les documents Frappe
- api.py: Endpoints API whitelistés
"""
from __future__ import annotations

# Re-export pour rétrocompatibilité avec l'ancien sms_utils.py
from ovh_sms_integration.utils.core import (
    get_ovh_sms_settings,
    send_bulk_sms,
    send_sms,
)
from ovh_sms_integration.utils.phone import (
    get_contact_mobile,
    get_customer_mobile_number,
    get_employee_mobile_number,
    validate_phone_number,
)
from ovh_sms_integration.utils.templates import (
    format_event_reminder_message,
    format_message_template,
    format_sms_message,
)
from ovh_sms_integration.utils.events import (
    get_event_participants_with_mobile,
    get_events_requiring_reminders,
    log_event_reminder_sent,
    process_pending_event_reminders,
    send_event_reminder_sms,
    update_reminder_statistics,
)
from ovh_sms_integration.utils.hooks import (
    on_document_cancel,
    on_document_submit,
    on_document_update,
    send_delivery_sms,
    send_payment_confirmation_sms,
    send_purchase_order_sms,
    send_sales_order_sms,
)
from ovh_sms_integration.utils.api import (
    get_pending_events,
    get_reminder_statistics,
    get_sms_balance,
    manual_send_event_reminder,
    send_manual_sms,
    send_test_reminder,
    test_ovh_connection,
)

__all__ = [
    # Core
    "get_ovh_sms_settings",
    "send_sms",
    "send_bulk_sms",
    # Phone
    "validate_phone_number",
    "get_contact_mobile",
    "get_customer_mobile_number",
    "get_employee_mobile_number",
    # Templates
    "format_message_template",
    "format_event_reminder_message",
    "format_sms_message",
    # Events
    "get_events_requiring_reminders",
    "get_event_participants_with_mobile",
    "send_event_reminder_sms",
    "log_event_reminder_sent",
    "process_pending_event_reminders",
    "update_reminder_statistics",
    # Hooks
    "on_document_update",
    "on_document_submit",
    "on_document_cancel",
    "send_sales_order_sms",
    "send_payment_confirmation_sms",
    "send_delivery_sms",
    "send_purchase_order_sms",
    # API
    "get_pending_events",
    "manual_send_event_reminder",
    "test_ovh_connection",
    "send_manual_sms",
    "get_sms_balance",
    "send_test_reminder",
    "get_reminder_statistics",
]

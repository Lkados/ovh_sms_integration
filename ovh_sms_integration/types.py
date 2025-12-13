# -*- coding: utf-8 -*-
"""Type definitions for ovh_sms_integration.

This module contains custom types used throughout the application
to improve type safety and code documentation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, TypedDict

if TYPE_CHECKING:
    from datetime import datetime

    from frappe.model.document import Document


class SMSResult(TypedDict, total=False):
    """Result of an SMS sending operation.

    Attributes:
            success: Whether the SMS was sent successfully
            message: Status or error message
            sender_used: The sender name/number actually used
            details: Additional details from the OVH API response
            sent: Number of SMS sent (for batch operations)
            failed: Number of SMS failed (for batch operations)
    """

    success: bool
    message: str
    sender_used: str | None
    details: dict[str, Any] | None
    sent: int
    failed: int


class EventData(TypedDict, total=False):
    """Event data structure from Frappe Event doctype.

    Attributes:
            name: Event ID
            subject: Event title
            description: Event description (may contain structured data)
            starts_on: Event start datetime
            ends_on: Event end datetime
            location: Event location
            event_participants: JSON string of participants
    """

    name: str
    subject: str
    description: str | None
    starts_on: datetime
    ends_on: datetime | None
    location: str | None
    event_participants: str | None


class ContactInfo(TypedDict):
    """Contact information structure.

    Attributes:
            name: Contact name
            mobile: Mobile phone number
            doc: Frappe document (Customer, Employee, etc.)
    """

    name: str
    mobile: str
    doc: Document


class EventParticipant(TypedDict):
    """Event participant information with mobile number.

    Attributes:
            name: Participant name
            mobile: Mobile phone number
            type: Type of participant (customer or employee)
            doctype: Frappe doctype (Customer, Employee, etc.)
            docname: Name/ID of the participant document
    """

    name: str
    mobile: str
    type: RecipientType
    doctype: str
    docname: str


class ReminderStats(TypedDict, total=False):
    """Reminder statistics structure.

    Attributes:
            enabled: Whether reminders are enabled
            total_sent: Total number of reminders sent all time
            sent_today: Number of reminders sent today
            failed_count: Total number of failed reminders
            last_sent: Datetime of last successful reminder
            last_check: Datetime of last check
            next_check: Datetime of next scheduled check
    """

    enabled: bool
    total_sent: int
    sent_today: int
    failed_count: int
    last_sent: datetime | None
    last_check: datetime | None
    next_check: datetime | None


class ParsedEventData(TypedDict, total=False):
    """Parsed structured data from event description.

    Attributes:
            client: Client name
            reference: Reference number
            type: Event type (Entretien, Livraison, etc.)
            article: Article/product name
            tel_client: Client phone number
            email_client: Client email
            appareil: Equipment/device name
            camion_requis: Whether a truck is required (Oui/Non)
    """

    client: str
    reference: str
    type: str
    article: str
    tel_client: str
    email_client: str
    appareil: str
    camion_requis: str


class CampaignStats(TypedDict):
    """Campaign statistics structure.

    Attributes:
            total_items: Total number of items in campaign
            total_customers: Number of unique customers
            total_sms_cost: Estimated SMS cost
            estimated_revenue: Estimated total revenue
            profit_potential: Estimated total profit
            average_margin_percent: Average margin percentage
    """

    total_items: int
    total_customers: int
    total_sms_cost: float
    estimated_revenue: float
    profit_potential: float
    average_margin_percent: float


class WeeklyReportStats(TypedDict, total=False):
    """Weekly report statistics structure.

    Attributes:
            events_scheduled: Number of events scheduled this week
            reminders_sent: Number of reminders sent this week
            total_reminders: Total reminders sent all time
            failed_reminders: Total failed reminders
            week_start: Week start date string
            week_end: Week end date string
    """

    events_scheduled: int
    reminders_sent: int
    total_reminders: int
    failed_reminders: int
    week_start: str
    week_end: str


# Literal types for better type safety
RecipientType = Literal["customer", "employee"]
CampaignStatus = Literal["Brouillon", "Prêt", "Partiellement envoyé", "Envoyé"]
SMSStatus = Literal["Envoyé", "Échoué", "En attente"]

__all__ = [
    "SMSResult",
    "EventData",
    "ContactInfo",
    "EventParticipant",
    "ReminderStats",
    "ParsedEventData",
    "CampaignStats",
    "WeeklyReportStats",
    "RecipientType",
    "CampaignStatus",
    "SMSStatus",
]

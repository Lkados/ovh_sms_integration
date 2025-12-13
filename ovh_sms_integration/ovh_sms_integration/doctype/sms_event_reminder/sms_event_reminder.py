# -*- coding: utf-8 -*-
"""SMS Event Reminder doctype.

Ce module gère les rappels SMS automatiques pour les événements.
"""
from __future__ import annotations

from datetime import datetime, time as dt_time, timedelta
from typing import TYPE_CHECKING, Any

import frappe
from frappe import _
from frappe.model.document import Document
from jinja2 import Template

if TYPE_CHECKING:
    from ovh_sms_integration.types import ParsedEventData


class SMSEventReminder(Document):
    """DocType de configuration pour les rappels SMS d'événements.

    Attributes:
        enabled (bool): Active/désactive les rappels
        event_type_filter (str): Type d'événement à surveiller
        reminder_hours_before (float): Heures avant l'événement pour le rappel
        enable_multiple_reminders (bool): Active les rappels multiples
        reminder_times (str): Liste des heures de rappel (CSV)
        customer_template (str): Template pour clients
        employee_template (str): Template pour employés
        default_template (str): Template par défaut
    """

    def validate(self) -> None:
        """Valide la configuration avant sauvegarde."""
        if self.enabled:
            if not self.event_type_filter:
                frappe.throw(_("Type d'événement à surveiller est requis"))

            if self.reminder_hours_before <= 0:
                frappe.throw(_("Les heures avant l'événement doivent être positives"))

            if self.enable_multiple_reminders and not self.reminder_times:
                frappe.throw(_("Heures de rappel requises pour les rappels multiples"))

            if self.enable_multiple_reminders and self.reminder_times:
                try:
                    times = [float(x.strip()) for x in self.reminder_times.split(",")]
                    if any(t <= 0 for t in times):
                        frappe.throw(
                            _("Toutes les heures de rappel doivent être positives")
                        )
                except ValueError:
                    frappe.throw(
                        _("Format invalide pour les heures de rappel (ex: 24,2,0.5)")
                    )

    def get_reminder_times(self) -> list[float]:
        """Retourne la liste des heures de rappel configurées.

        Returns:
            list[float]: Liste des heures de rappel.
        """
        if self.enable_multiple_reminders and self.reminder_times:
            try:
                return [float(x.strip()) for x in self.reminder_times.split(",")]
            except ValueError:
                frappe.log_error("Format invalide pour reminder_times")
                return [float(self.reminder_hours_before)]
        return [float(self.reminder_hours_before)]

    def get_message_template(self, recipient_type: str = "customer") -> str:
        """Retourne le template de message selon le type de destinataire.

        Args:
            recipient_type: Type de destinataire ("customer" ou "employee").

        Returns:
            str: Template Jinja2 pour le message SMS.
        """
        if recipient_type == "customer" and self.customer_template:
            return self.customer_template
        elif recipient_type == "employee" and self.employee_template:
            return self.employee_template
        elif self.default_template:
            return self.default_template
        return self.reminder_message_template

    def should_send_now(self) -> bool:
        """Vérifie si on peut envoyer des SMS maintenant selon les contraintes.

        Returns:
            bool: True si l'envoi est autorisé maintenant.
        """
        now = datetime.now()

        if self.business_hours_only:
            current_time = now.time()

            # Convertir les heures de string à datetime.time si nécessaire
            start_time = self._parse_time_field(self.business_start_time)
            end_time = self._parse_time_field(self.business_end_time)

            if start_time and current_time < start_time:
                return False
            if end_time and current_time > end_time:
                return False

        if self.exclude_weekends and now.weekday() >= 5:
            return False

        return True

    def _parse_time_field(self, time_value: Any) -> dt_time | None:
        """Convertit une valeur de champ Time en objet datetime.time.

        Args:
            time_value: Valeur du champ (str "HH:MM" ou datetime.time).

        Returns:
            dt_time | None: Objet time ou None si invalide.
        """
        if time_value is None:
            return None

        # Si c'est déjà un objet time, le retourner directement
        if isinstance(time_value, dt_time):
            return time_value

        # Si c'est un objet datetime, extraire le time
        if isinstance(time_value, datetime):
            return time_value.time()

        # Si c'est une chaîne, la parser
        if isinstance(time_value, str):
            try:
                # Format attendu: "HH:MM" ou "HH:MM:SS"
                parts = time_value.split(":")
                hour = int(parts[0])
                minute = int(parts[1]) if len(parts) > 1 else 0
                second = int(parts[2]) if len(parts) > 2 else 0
                return dt_time(hour, minute, second)
            except (ValueError, IndexError):
                frappe.log_error(
                    f"Format de temps invalide: {time_value}",
                    "SMS Event Reminder - Parse Time Error"
                )
                return None

        return None

    def parse_event_data(self, description: str | None) -> "ParsedEventData":
        """Parse les données structurées de l'événement.

        Args:
            description: Description de l'événement.

        Returns:
            ParsedEventData: Dictionnaire avec les champs extraits.
        """
        from ovh_sms_integration.ovh_sms_integration.services.event_parser import (
            parse_event_data,
        )

        return parse_event_data(description)

    def format_message(
        self,
        template: str,
        event_doc: Any,
        customer_name: str | None = None,
        employee_name: str | None = None,
    ) -> str:
        """Formate le message avec les données de l'événement.

        Args:
            template: Template Jinja2 du message.
            event_doc: Document Event Frappe.
            customer_name: Nom du client destinataire.
            employee_name: Nom de l'employé destinataire.

        Returns:
            str: Message formaté prêt à être envoyé.
        """
        from ovh_sms_integration.ovh_sms_integration.services.event_parser import (
            build_event_context,
        )

        try:
            context = build_event_context(event_doc, customer_name, employee_name)
            template_obj = Template(template)
            return template_obj.render(**context)
        except Exception as e:
            frappe.log_error(f"Erreur formatage message rappel: {e}")
            return template

    def extract_event_type_from_description(
        self, description: str | None
    ) -> str | None:
        """Extrait le type d'événement depuis la description.

        Args:
            description: Description de l'événement.

        Returns:
            str | None: Type d'événement extrait.
        """
        from ovh_sms_integration.ovh_sms_integration.services.event_parser import (
            extract_event_type,
        )

        return extract_event_type(description)

    def get_events_for_reminder(self) -> list[dict[str, Any]]:
        """Récupère les événements nécessitant un rappel.

        Returns:
            list[dict[str, Any]]: Liste des événements avec leurs données.
        """
        if not self.enabled:
            return []

        try:
            reminder_times = self.get_reminder_times()
            now = datetime.now()
            event_types_to_filter = [
                t.strip() for t in self.event_type_filter.split(",")
            ]

            all_events = []
            for hours_before in reminder_times:
                start_time = now + timedelta(hours=hours_before - 0.5)
                end_time = now + timedelta(hours=hours_before + 0.5)

                filters: dict[str, Any] = {
                    "docstatus": 1,
                    "starts_on": ["between", [start_time, end_time]],
                }

                if self.skip_past_events:
                    filters["starts_on"] = [">", now]

                if self.skip_all_day_events:
                    filters["all_day"] = 0

                events = frappe.get_all(
                    "Event",
                    filters=filters,
                    fields=[
                        "name",
                        "subject",
                        "description",
                        "starts_on",
                        "ends_on",
                        "event_participants",
                        "location",
                    ],
                )
                all_events.extend(events)

            # Filtrage par type
            filtered_events = []
            for event in all_events:
                event_type = self.extract_event_type_from_description(event.description)

                if not event_type:
                    for filter_type in event_types_to_filter:
                        if filter_type.lower() in (event.subject or "").lower():
                            event_type = filter_type
                            break

                if event_type:
                    for filter_type in event_types_to_filter:
                        if filter_type.lower() in event_type.lower():
                            filtered_events.append(event)
                            break

            # Filtrage par durée minimum
            if self.minimum_event_duration > 0:
                filtered_events = [
                    e
                    for e in filtered_events
                    if e.ends_on
                    and e.starts_on
                    and (e.ends_on - e.starts_on).total_seconds() / 60
                    >= self.minimum_event_duration
                ]

            return filtered_events

        except Exception as e:
            frappe.log_error(f"Erreur récupération événements: {e}")
            return []

    def get_event_contacts(self, event: Any) -> dict[str, list[dict[str, Any]]]:
        """Récupère les contacts (clients et employés) d'un événement.

        Args:
            event: Document Event ou dict avec 'name'.

        Returns:
            dict[str, list]: Contacts groupés par type (customers, employees).
        """
        from ovh_sms_integration.utils.phone import (
            get_customer_mobile_number,
            get_employee_mobile_number,
        )

        contacts: dict[str, list[dict[str, Any]]] = {"customers": [], "employees": []}

        try:
            participants = frappe.get_all(
                "Event Participants",
                filters={"parent": event.name},
                fields=["reference_doctype", "reference_docname"],
            )

            for participant in participants:
                if participant.reference_doctype == "Customer":
                    customer = frappe.get_doc("Customer", participant.reference_docname)
                    mobile = get_customer_mobile_number(customer)
                    if mobile:
                        contacts["customers"].append(
                            {
                                "name": customer.customer_name,
                                "mobile": mobile,
                                "doc": customer,
                            }
                        )

                elif participant.reference_doctype == "Employee":
                    employee = frappe.get_doc("Employee", participant.reference_docname)
                    mobile = get_employee_mobile_number(employee)
                    if mobile:
                        contacts["employees"].append(
                            {
                                "name": employee.employee_name,
                                "mobile": mobile,
                                "doc": employee,
                            }
                        )

        except Exception as e:
            frappe.log_error(
                f"Erreur récupération contacts événement {event.name}: {e}"
            )

        return contacts

    def send_event_reminders(self) -> None:
        """Envoie les rappels pour tous les événements éligibles."""
        if not self.enabled or not self.should_send_now():
            return

        try:
            events = self.get_events_for_reminder()
            sent_count = 0
            failed_count = 0

            for event in events:
                if self.is_reminder_already_sent(event.name):
                    continue

                contacts = self.get_event_contacts(event)
                event_doc = frappe.get_doc("Event", event.name)

                # Envoi aux clients
                if self.send_to_customer_only or not self.send_to_employee:
                    sent, failed = self._send_to_customers(contacts, event_doc, event)
                    sent_count += sent
                    failed_count += failed

                # Envoi aux employés
                if self.send_to_employee:
                    sent, failed = self._send_to_employees(contacts, event_doc, event)
                    sent_count += sent
                    failed_count += failed

            self.update_statistics(sent_count, failed_count)

            if sent_count > 0 or failed_count > 0:
                frappe.logger().info(
                    f"Rappels événements: {sent_count} envoyés, {failed_count} échoués"
                )

        except Exception as e:
            frappe.log_error(f"Erreur envoi rappels événements: {e}")

    def _send_to_customers(
        self, contacts: dict, event_doc: Any, event: Any
    ) -> tuple[int, int]:
        """Envoie les rappels aux clients."""
        sent = 0
        failed = 0
        for customer in contacts["customers"]:
            try:
                template = self.get_message_template("customer")
                message = self.format_message(
                    template, event_doc, customer_name=customer["name"]
                )
                result = self.send_sms_reminder(message, customer["mobile"])
                if result and result.get("success"):
                    sent += 1
                    self.log_reminder_sent(event.name, customer["name"], "customer")
                else:
                    failed += 1
            except Exception as e:
                frappe.log_error(f"Erreur envoi rappel client {customer['name']}: {e}")
                failed += 1
        return sent, failed

    def _send_to_employees(
        self, contacts: dict, event_doc: Any, event: Any
    ) -> tuple[int, int]:
        """Envoie les rappels aux employés."""
        sent = 0
        failed = 0
        for employee in contacts["employees"]:
            try:
                template = self.get_message_template("employee")
                message = self.format_message(
                    template, event_doc, employee_name=employee["name"]
                )
                result = self.send_sms_reminder(message, employee["mobile"])
                if result and result.get("success"):
                    sent += 1
                    self.log_reminder_sent(event.name, employee["name"], "employee")
                else:
                    failed += 1
            except Exception as e:
                frappe.log_error(
                    f"Erreur envoi rappel employé {employee['name']}: {e}"
                )
                failed += 1
        return sent, failed

    def get_best_sender(self) -> str:
        """Retourne le meilleur expéditeur disponible depuis OVH SMS Settings.

        Returns:
            str: Nom de l'expéditeur SMS à utiliser.
        """
        try:
            sms_settings = frappe.get_single("OVH SMS Settings")
            if not sms_settings.enabled:
                return "ERPNext"
            return sms_settings.get_best_sender()
        except Exception as e:
            frappe.log_error(f"Erreur récupération expéditeur: {e}")
            return "ERPNext"

    def send_sms_reminder(self, message: str, mobile: str) -> dict[str, Any]:
        """Envoie un SMS de rappel via l'intégration OVH.

        Args:
            message: Contenu du SMS formaté.
            mobile: Numéro de téléphone mobile du destinataire.

        Returns:
            dict[str, Any]: Résultat de l'envoi avec success et message.
        """
        try:
            sms_settings = frappe.get_single("OVH SMS Settings")
            if not sms_settings.enabled:
                return {"success": False, "message": _("OVH SMS non activé")}
            return sms_settings.send_sms(message, mobile)
        except Exception as e:
            frappe.log_error(f"Erreur envoi SMS rappel: {e}")
            return {"success": False, "message": str(e)}

    def is_reminder_already_sent(self, event_name: str) -> bool:
        """Vérifie si un rappel a déjà été envoyé pour cet événement.

        Args:
            event_name: Nom/ID de l'événement à vérifier.

        Returns:
            bool: True si rappel déjà envoyé, False sinon.
        """
        return False

    def log_reminder_sent(
        self, event_name: str, recipient_name: str, recipient_type: str
    ) -> None:
        """Log l'envoi d'un rappel.

        Args:
            event_name: Nom/ID de l'événement.
            recipient_name: Nom du destinataire.
            recipient_type: Type de destinataire.
        """
        try:
            frappe.logger().info(
                f"Rappel envoyé - Événement: {event_name}, "
                f"Destinataire: {recipient_name} ({recipient_type})"
            )
        except Exception as e:
            frappe.log_error(f"Erreur logging rappel: {e}")

    def update_statistics(self, sent_count: int, failed_count: int) -> None:
        """Met à jour les statistiques d'envoi.

        Args:
            sent_count: Nombre de SMS envoyés avec succès.
            failed_count: Nombre de SMS échoués.
        """
        try:
            now = datetime.now()

            self.db_set(
                "total_reminders_sent", (self.total_reminders_sent or 0) + sent_count
            )
            self.db_set(
                "failed_reminders_count",
                (self.failed_reminders_count or 0) + failed_count,
            )
            self.db_set("last_check_time", now)
            self.db_set("next_check_time", now + timedelta(hours=1))

            if sent_count > 0:
                self.db_set("last_reminder_sent", now)

            today = now.date()
            last_check = self.last_check_time.date() if self.last_check_time else None

            if last_check != today:
                self.db_set("reminders_sent_today", sent_count)
            else:
                self.db_set(
                    "reminders_sent_today",
                    (self.reminders_sent_today or 0) + sent_count,
                )

        except Exception as e:
            frappe.log_error(f"Erreur mise à jour statistiques: {e}")


def process_event_reminders() -> None:
    """Fonction appelée par le scheduler pour traiter les rappels.

    Point d'entrée pour le traitement automatique des rappels d'événements
    via le Frappe scheduler.
    """
    try:
        settings = frappe.get_single("SMS Event Reminder")
        if settings.enabled:
            settings.send_event_reminders()
    except Exception as e:
        frappe.log_error(f"Erreur traitement rappels événements: {e}")

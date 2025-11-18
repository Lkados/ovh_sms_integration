# -*- coding: utf-8 -*-
"""SMS utilities for OVH SMS Integration.

This module provides core functionality for sending SMS, validating phone numbers,
formatting messages with templates, and extracting contact information.
"""

from __future__ import unicode_literals

import json
import re
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import frappe
from frappe import _

if TYPE_CHECKING:
	from frappe.model.document import Document

	from ovh_sms_integration.types import EventParticipant, RecipientType, SMSResult


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

	Note:
		Cette fonction ne lève pas d'exception si le document
		n'existe pas, elle retourne simplement None.
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

	Cette fonction principale gère tout le processus d'envoi SMS :
	- Vérification de la configuration OVH
	- Formatage du message avec template Jinja2 si contexte fourni
	- Validation et normalisation du numéro de téléphone
	- Envoi effectif via l'API OVH

	Args:
		message: Contenu du SMS (peut contenir des variables Jinja2).
		receiver: Numéro de téléphone du destinataire.
			Formats acceptés: "0612345678", "+33612345678".
		sender: Nom de l'expéditeur SMS (optionnel).
			Si None, utilise le sender par défaut configuré.
		context: Dictionnaire de variables pour le template Jinja2.
			Example: {"name": "Jean", "date": "15/01/2025"}.

	Returns:
		SMSResult: Dictionnaire contenant:
			- success (bool): True si envoi réussi
			- message (str): Message de statut
			- sender_used (str): Expéditeur effectivement utilisé
			- details (dict): Réponse complète de l'API OVH
		None: Si erreur ou intégration désactivée.

	Example:
		>>> # Envoi simple
		>>> result = send_sms(
		...     message="Votre RDV est confirmé",
		...     receiver="0612345678"
		... )
		>>>
		>>> # Envoi avec template
		>>> result = send_sms(
		...     message="Bonjour {{name}}, RDV le {{date}}",
		...     receiver="+33612345678",
		...     context={"name": "Jean", "date": "15/01/2025"}
		... )
		>>>
		>>> if result and result["success"]:
		...     print(f"SMS envoyé via {result['sender_used']}")

	Raises:
		ValueError: Si le numéro de téléphone est invalide.

	Note:
		Les erreurs d'envoi sont loguées mais ne lèvent pas d'exception.
		La fonction retourne None en cas d'erreur.
	"""
	settings = get_ovh_sms_settings()
	if not settings:
		frappe.log_error(_("OVH SMS non configuré"))
		return None

	try:
		# Formatage du message avec le contexte
		formatted_message: str = message
		if context:
			formatted_message = format_message_template(message, context)

		# Validation du numéro
		validated_receiver: str = validate_phone_number(receiver)

		# Envoi du SMS
		result: "SMSResult" = settings.send_sms(formatted_message, validated_receiver, sender)
		return result

	except ValueError as e:
		# Erreur de validation du numéro
		frappe.log_error(_("Numéro de téléphone invalide: {0}").format(str(e)))
		raise
	except Exception as e:
		# Autres erreurs
		frappe.log_error(_("Erreur envoi SMS: {0}").format(str(e)))
		return None


def format_message_template(template: str, context: dict[str, Any]) -> str:
	"""Formate un template de message avec les données du contexte.

	Utilise Jinja2 pour remplacer les variables dans le template.
	Sécurise automatiquement les valeurs du contexte en convertissant
	les types complexes en chaînes de caractères.

	Args:
		template: Template Jinja2 avec variables entre {{ }}.
			Example: "Bonjour {{name}}, RDV le {{date}}".
		context: Dictionnaire des variables à injecter.
			Keys: noms des variables.
			Values: valeurs (str, int, float, datetime, ou autre).

	Returns:
		str: Message avec variables remplacées par leurs valeurs.
			Template original si erreur de formatage.

	Example:
		>>> template = "Bonjour {{name}}, votre solde est {{amount}}€"
		>>> context = {"name": "Jean", "amount": 150.50}
		>>> result = format_message_template(template, context)
		>>> print(result)
		"Bonjour Jean, votre solde est 150.5€"

		>>> # Avec datetime
		>>> from datetime import datetime
		>>> context = {
		...     "name": "Marie",
		...     "date": datetime(2025, 1, 15, 14, 30)
		... }
		>>> template = "{{name}}, RDV le {{date}}"
		>>> result = format_message_template(template, context)
		>>> print(result)
		"Marie, RDV le 15/01/2025 14:30"

	Note:
		- Les datetime sont automatiquement formatés en 'DD/MM/YYYY HH:MM'
		- Les autres objets sont convertis en str
		- En cas d'erreur, retourne le template original inchangé
	"""
	if not template or not context:
		return template

	try:
		from jinja2 import Template

		# Sécurisation des données
		safe_context: dict[str, str | int | float] = {}
		for key, value in context.items():
			if isinstance(value, (str, int, float)):
				safe_context[key] = value
			elif hasattr(value, "strftime"):  # datetime
				safe_context[key] = value.strftime("%d/%m/%Y %H:%M")
			else:
				safe_context[key] = str(value)

		template_obj: Template = Template(template)
		return template_obj.render(**safe_context)

	except Exception as e:
		frappe.log_error(_("Erreur formatage template: {0}").format(str(e)))
		return template


def validate_phone_number(phone: str | None) -> str:
	"""Valide et normalise un numéro de téléphone au format international.

	Nettoie le numéro (supprime espaces, tirets, parenthèses),
	convertit les numéros français au format international +33,
	et valide le format final.

	Args:
		phone: Numéro de téléphone à valider.
			Formats acceptés:
			- "0612345678" (français)
			- "+33612345678" (international)
			- "06 12 34 56 78" (avec espaces)
			- "06-12-34-56-78" (avec tirets)

	Returns:
		str: Numéro au format international +33XXXXXXXXX.

	Example:
		>>> validate_phone_number("0612345678")
		'+33612345678'

		>>> validate_phone_number("+33 6 12 34 56 78")
		'+33612345678'

		>>> validate_phone_number("612345678")
		'+33612345678'

	Raises:
		ValueError: Si le numéro est None, vide ou invalide.

	Note:
		- Spécifique au format français (+33)
		- Accepte les numéros de 10 à 15 chiffres après le code pays
		- Pour d'autres pays, adapter la logique de préfixe
	"""
	if not phone:
		raise ValueError(_("Numéro de téléphone vide"))

	# Nettoyage du numéro (garde seulement chiffres et +)
	cleaned_phone: str = re.sub(r"[^\d+]", "", str(phone))

	# Conversion au format international français
	if cleaned_phone.startswith("0"):
		# Format français local -> international
		cleaned_phone = "+33" + cleaned_phone[1:]
	elif not cleaned_phone.startswith("+"):
		# Pas de préfixe -> ajouter +33
		cleaned_phone = "+33" + cleaned_phone

	# Validation du format final
	if not re.match(r"^\+\d{10,15}$", cleaned_phone):
		raise ValueError(
			_("Numéro de téléphone invalide: {0}. Format attendu: +33XXXXXXXXX").format(phone)
		)

	return cleaned_phone


def get_contact_mobile(doc: "Document") -> str | None:
	"""Récupère le numéro de mobile depuis un document Frappe.

	Recherche le numéro mobile en parcourant plusieurs champs
	standards, puis les contacts liés si nécessaire.

	Args:
		doc: Document Frappe (Customer, Supplier, etc.).
			Doit avoir au moins un des champs mobiles standards.

	Returns:
		str: Numéro de mobile trouvé (non validé).
		None: Si aucun numéro trouvé.

	Example:
		>>> customer = frappe.get_doc("Customer", "CUST-001")
		>>> mobile = get_contact_mobile(customer)
		>>> if mobile:
		...     send_sms("Message", mobile)

	Note:
		Champs recherchés dans l'ordre:
		1. mobile_no, phone_no, contact_mobile, mobile, phone (sur le doc)
		2. contact_person lié (mêmes champs)

		Le numéro retourné n'est pas validé/normalisé.
		Utiliser validate_phone_number() avant envoi SMS.
	"""
	mobile_fields: list[str] = ["mobile_no", "phone_no", "contact_mobile", "mobile", "phone"]

	# Recherche dans les champs du document
	for field in mobile_fields:
		if hasattr(doc, field) and doc.get(field):
			return doc.get(field)

	# Recherche dans les contacts liés
	if hasattr(doc, "contact_person") and doc.contact_person:
		try:
			contact: "Document" = frappe.get_doc("Contact", doc.contact_person)
			for field in mobile_fields:
				if hasattr(contact, field) and contact.get(field):
					return contact.get(field)
		except Exception as e:
			frappe.log_error(_("Erreur récupération contact {0}: {1}").format(doc.contact_person, str(e)))

	return None

# === HANDLERS POUR LES ÉVÉNEMENTS DE DOCUMENTS ===


def on_document_update(doc: "Document", method: str | None = None) -> None:
	"""Handler générique pour les mises à jour de documents.

	Ce handler est appelé automatiquement par Frappe lors de la mise à jour
	d'un document (hook on_update).

	Args:
		doc: Document Frappe mis à jour.
		method: Nom de la méthode appelante (fourni par Frappe).
			Non utilisé dans cette implémentation.

	Note:
		Actuellement non implémenté. Peut être étendu pour ajouter
		des notifications SMS lors de mises à jour de documents.
	"""
	pass


def on_document_submit(doc: "Document", method: str | None = None) -> None:
	"""Handler générique pour les soumissions de documents.

	Ce handler est appelé automatiquement par Frappe lors de la soumission
	d'un document (hook on_submit).

	Args:
		doc: Document Frappe soumis.
		method: Nom de la méthode appelante (fourni par Frappe).
			Non utilisé dans cette implémentation.

	Note:
		Actuellement non implémenté. Peut être étendu pour ajouter
		des notifications SMS lors de soumissions de documents.
	"""
	pass


def on_document_cancel(doc: "Document", method: str | None = None) -> None:
	"""Handler générique pour les annulations de documents.

	Ce handler est appelé automatiquement par Frappe lors de l'annulation
	d'un document (hook on_cancel).

	Args:
		doc: Document Frappe annulé.
		method: Nom de la méthode appelante (fourni par Frappe).
			Non utilisé dans cette implémentation.

	Note:
		Actuellement non implémenté. Peut être étendu pour ajouter
		des notifications SMS lors d'annulations de documents.
	"""
	pass


def send_sales_order_sms(doc: "Document", method: str | None = None) -> None:
	"""Envoie un SMS de confirmation lors de la soumission d'une commande client.

	Cette fonction est appelée automatiquement lors de la soumission
	d'une Sales Order. Elle envoie un SMS au client avec les détails
	de la commande si l'option est activée dans les paramètres.

	Args:
		doc: Document Sales Order soumis.
		method: Nom de la méthode appelante (fourni par Frappe).
			Non utilisé dans cette implémentation.

	Example:
		Configuration dans hooks.py:
		```python
		doc_events = {
		    "Sales Order": {
		        "on_submit": "ovh_sms_integration.utils.sms_utils.send_sales_order_sms"
		    }
		}
		```

	Note:
		L'envoi ne se fait que si:
		- L'intégration OVH SMS est configurée
		- L'option enable_sales_order_sms est activée
		- Un numéro de mobile valide est trouvé pour le client
	"""
	settings = get_ovh_sms_settings()
	if not settings or not settings.enable_sales_order_sms:
		return

	mobile = get_contact_mobile(doc)
	if not mobile:
		return

	template = settings.sales_order_template
	context = {
		"name": doc.name,
		"customer": doc.customer,
		"grand_total": doc.grand_total,
		"currency": doc.currency,
		"transaction_date": doc.transaction_date,
	}

	send_sms(template, mobile, context=context)


def send_payment_confirmation_sms(doc: "Document", method: str | None = None) -> None:
	"""Envoie un SMS de confirmation lors de la confirmation d'un paiement.

	Cette fonction est appelée automatiquement lors de la soumission
	d'un Payment Entry. Elle envoie un SMS au client avec les détails
	du paiement si l'option est activée dans les paramètres.

	Args:
		doc: Document Payment Entry soumis.
		method: Nom de la méthode appelante (fourni par Frappe).
			Non utilisé dans cette implémentation.

	Example:
		Configuration dans hooks.py:
		```python
		doc_events = {
		    "Payment Entry": {
		        "on_submit": "ovh_sms_integration.utils.sms_utils.send_payment_confirmation_sms"
		    }
		}
		```

	Note:
		L'envoi ne se fait que si:
		- L'intégration OVH SMS est configurée
		- L'option enable_payment_sms est activée
		- Un numéro de mobile valide est trouvé pour le client
	"""
	settings = get_ovh_sms_settings()
	if not settings or not settings.enable_payment_sms:
		return

	mobile = get_contact_mobile(doc)
	if not mobile:
		return

	template = settings.payment_template
	context = {
		"name": doc.name,
		"paid_amount": doc.paid_amount,
		"currency": doc.paid_from_account_currency,
		"posting_date": doc.posting_date,
	}

	send_sms(template, mobile, context=context)


def send_delivery_sms(doc: "Document", method: str | None = None) -> None:
	"""Envoie un SMS de notification lors de l'expédition.

	Cette fonction est appelée automatiquement lors de la soumission
	d'un Delivery Note. Elle envoie un SMS au client pour l'informer
	de l'expédition si l'option est activée dans les paramètres.

	Args:
		doc: Document Delivery Note soumis.
		method: Nom de la méthode appelante (fourni par Frappe).
			Non utilisé dans cette implémentation.

	Example:
		Configuration dans hooks.py:
		```python
		doc_events = {
		    "Delivery Note": {
		        "on_submit": "ovh_sms_integration.utils.sms_utils.send_delivery_sms"
		    }
		}
		```

	Note:
		L'envoi ne se fait que si:
		- L'intégration OVH SMS est configurée
		- L'option enable_delivery_sms est activée
		- Un numéro de mobile valide est trouvé pour le client
	"""
	settings = get_ovh_sms_settings()
	if not settings or not settings.enable_delivery_sms:
		return

	mobile = get_contact_mobile(doc)
	if not mobile:
		return

	template = settings.delivery_template
	context = {
		"name": doc.name,
		"customer": doc.customer,
		"posting_date": doc.posting_date,
	}

	send_sms(template, mobile, context=context)


def send_purchase_order_sms(doc: "Document", method: str | None = None) -> None:
	"""Envoie un SMS de notification lors de la soumission d'une commande fournisseur.

	Cette fonction est appelée automatiquement lors de la soumission
	d'un Purchase Order. Elle envoie un SMS au fournisseur avec les détails
	de la commande si l'option est activée dans les paramètres.

	Args:
		doc: Document Purchase Order soumis.
		method: Nom de la méthode appelante (fourni par Frappe).
			Non utilisé dans cette implémentation.

	Example:
		Configuration dans hooks.py:
		```python
		doc_events = {
		    "Purchase Order": {
		        "on_submit": "ovh_sms_integration.utils.sms_utils.send_purchase_order_sms"
		    }
		}
		```

	Note:
		L'envoi ne se fait que si:
		- L'intégration OVH SMS est configurée
		- L'option enable_purchase_order_sms est activée
		- Un numéro de mobile valide est trouvé pour le fournisseur
	"""
	settings = get_ovh_sms_settings()
	if not settings or not settings.enable_purchase_order_sms:
		return

	mobile = get_contact_mobile(doc)
	if not mobile:
		return

	template = settings.purchase_order_template
	context = {
		"name": doc.name,
		"supplier": doc.supplier,
		"supplier_name": doc.supplier_name,
		"grand_total": doc.grand_total,
		"currency": doc.currency,
		"transaction_date": doc.transaction_date,
	}

	send_sms(template, mobile, context=context)

# === NOUVELLES FONCTIONS POUR LES RAPPELS D'ÉVÉNEMENTS ===


def send_event_reminder_sms(
	event_doc: "Document",
	recipient_mobile: str,
	recipient_name: str,
	recipient_type: "RecipientType" = "customer",
) -> "SMSResult":
	"""Envoie un rappel SMS pour un événement spécifique à un participant.

	Cette fonction gère l'envoi d'un rappel SMS personnalisé pour un événement
	à un participant donné (client ou employé).

	Args:
		event_doc: Document Event Frappe contenant les détails de l'événement.
		recipient_mobile: Numéro de téléphone du destinataire.
			Format: "+33612345678".
		recipient_name: Nom du destinataire pour personnalisation du message.
		recipient_type: Type de destinataire ("customer" ou "employee").
			Détermine le template de message à utiliser.

	Returns:
		SMSResult: Dictionnaire avec:
			- success (bool): True si envoi réussi
			- message (str): Message de statut ou d'erreur

	Example:
		>>> event = frappe.get_doc("Event", "EVT-001")
		>>> result = send_event_reminder_sms(
		...     event,
		...     "+33612345678",
		...     "Jean Dupont",
		...     "customer"
		... )
		>>> if result["success"]:
		...     print("Rappel envoyé")

	Note:
		- L'envoi est loggé automatiquement en cas de succès
		- Les erreurs sont loggées mais ne lèvent pas d'exception
	"""
	try:
		reminder_settings = frappe.get_single("SMS Event Reminder")

		if not reminder_settings.enabled:
			return {"success": False, "message": "Rappels désactivés"}

		# Récupération du template approprié
		template = reminder_settings.get_message_template(recipient_type)

		# Formatage du message
		message = format_event_reminder_message(template, event_doc, recipient_name, recipient_type)

		# Envoi du SMS
		result = send_sms(message, recipient_mobile)

		if result and result.get("success"):
			log_event_reminder_sent(event_doc.name, recipient_name, recipient_type, recipient_mobile)
			return result

		# Fallback si result est None
		return result if result else {"success": False, "message": "Erreur envoi SMS", "sender_used": None, "details": None, "sent": 0, "failed": 1}

	except Exception as e:
		frappe.log_error(f"Erreur envoi rappel événement {event_doc.name}: {e}")
		return {"success": False, "message": str(e)}

def format_event_reminder_message(
	template: str,
	event_doc: "Document",
	recipient_name: str | None = None,
	recipient_type: "RecipientType" = "customer",
) -> str:
	"""Formate le message de rappel d'événement avec les variables Jinja2.

	Construit un contexte de données à partir de l'événement et le passe
	au template Jinja2 pour générer le message final.

	Args:
		template: Template Jinja2 du message.
			Variables disponibles: {{subject}}, {{start_date}}, {{start_time}},
			{{location}}, {{duration}}, {{customer_name}}, {{employee_name}}.
		event_doc: Document Event contenant les détails de l'événement.
		recipient_name: Nom du destinataire pour personnalisation.
			Optionnel, peut être None.
		recipient_type: Type de destinataire ("customer" ou "employee").
			Détermine quelle variable de nom sera remplie.

	Returns:
		str: Message formaté prêt à être envoyé.
			En cas d'erreur de formatage, retourne le template original.

	Example:
		>>> template = "Rappel: {{subject}} le {{start_date}} à {{start_time}}"
		>>> event = frappe.get_doc("Event", "EVT-001")
		>>> message = format_event_reminder_message(
		...     template,
		...     event,
		...     "Jean Dupont",
		...     "customer"
		... )
		>>> print(message)
		Rappel: Rendez-vous client le 15/01/2025 à 14:00

	Note:
		- Les valeurs None sont remplacées par des chaînes vides
		- La durée est calculée en minutes si ends_on est disponible
		- Les erreurs de formatage sont loggées
	"""
	try:
		context = {
			"subject": event_doc.subject or "",
			"description": event_doc.description or "",
			"event_name": event_doc.name,
			"start_date": event_doc.starts_on.strftime("%d/%m/%Y") if event_doc.starts_on else "",
			"start_time": event_doc.starts_on.strftime("%H:%M") if event_doc.starts_on else "",
			"location": getattr(event_doc, "location", "") or "",
			"customer_name": recipient_name if recipient_type == "customer" else "",
			"employee_name": recipient_name if recipient_type == "employee" else "",
		}

		# Calcul de la durée
		if event_doc.starts_on and event_doc.ends_on:
			duration = (event_doc.ends_on - event_doc.starts_on).total_seconds() / 60
			context["duration"] = int(duration)
		else:
			context["duration"] = ""

		return format_message_template(template, context)

	except Exception as e:
		frappe.log_error(f"Erreur formatage message rappel: {e}")
		return template

def get_events_requiring_reminders() -> list[dict[str, Any]]:
	"""Récupère les événements nécessitant un rappel SMS.

	Cette fonction identifie les événements à venir qui correspondent
	aux critères de rappel configurés (timing, filtre de type, etc.).

	Returns:
		list[dict]: Liste de dictionnaires d'événements avec les champs:
			- name (str): ID de l'événement
			- subject (str): Titre de l'événement
			- description (str): Description
			- starts_on (datetime): Date/heure de début
			- ends_on (datetime): Date/heure de fin
			- event_participants (str): JSON des participants
			- location (str): Lieu de l'événement
		Retourne [] si:
			- Les rappels sont désactivés
			- Aucun événement ne correspond
			- Une erreur survient

	Example:
		>>> events = get_events_requiring_reminders()
		>>> for event in events:
		...     print(f"Événement {event['name']} dans {event['starts_on']}")

	Note:
		- Utilise une marge de 30 minutes autour de chaque heure de rappel
		- Seuls les événements soumis (docstatus=1) sont retournés
		- Le filtre event_type_filter (ex: "entretien") est appliqué
		- TODO: Convertir SQL en ORM Frappe (frappe.get_all)
	"""
	try:
		reminder_settings = frappe.get_single("SMS Event Reminder")

		if not reminder_settings.enabled:
			return []

		# Calcul des heures de rappel
		reminder_times = reminder_settings.get_reminder_times()
		now = datetime.now()

		conditions = []
		for hours_before in reminder_times:
			start_time = now + timedelta(hours=hours_before - 0.5)  # Marge de 30min
			end_time = now + timedelta(hours=hours_before + 0.5)
			conditions.append(f"(starts_on BETWEEN '{start_time}' AND '{end_time}')")

		time_condition = " OR ".join(conditions)

		# Requête des événements
		# TODO: Convertir en ORM frappe.get_all avec filters
		events = frappe.db.sql(
			f"""
			SELECT name, subject, description, starts_on, ends_on,
				   event_participants, location
			FROM `tabEvent`
			WHERE ({time_condition})
			AND docstatus = 1
			AND subject LIKE %s
			AND starts_on > %s
		""",
			(f"%{reminder_settings.event_type_filter}%", now),
			as_dict=True,
		)

		return events

	except Exception as e:
		frappe.log_error(f"Erreur récupération événements rappels: {e}")
		return []

def get_event_participants_with_mobile(event_name: str) -> list["EventParticipant"]:
	"""Récupère les participants d'un événement avec leurs numéros mobiles.

	Cette fonction extrait tous les participants d'un événement (Customers et
	Employees) et récupère leurs numéros de téléphone mobile.

	Args:
		event_name: Nom/ID de l'événement Frappe.

	Returns:
		list[EventParticipant]: Liste de participants avec:
			- name (str): Nom du participant
			- mobile (str): Numéro de téléphone mobile
			- type (RecipientType): "customer" ou "employee"
			- doctype (str): Type de document ("Customer", "Employee")
			- docname (str): ID du document
		Retourne [] si aucun participant avec mobile n'est trouvé.

	Example:
		>>> participants = get_event_participants_with_mobile("EVT-001")
		>>> for p in participants:
		...     print(f"{p['name']}: {p['mobile']} ({p['type']})")
		Jean Dupont: +33612345678 (customer)
		Marie Martin: +33698765432 (employee)

	Note:
		- Seuls les participants avec un numéro mobile valide sont retournés
		- Les erreurs sont loggées mais ne lèvent pas d'exception
		- TODO: Convertir SQL en ORM (frappe.get_all)
	"""
	try:
		participants: list[EventParticipant] = []

		# Récupération des participants
		# TODO: Convertir en frappe.get_all
		event_participants = frappe.db.sql(
			"""
			SELECT reference_doctype, reference_docname
			FROM `tabEvent Participants`
			WHERE parent = %s
		""",
			event_name,
			as_dict=True,
		)

		for participant in event_participants:
			mobile = None
			name = None
			participant_type: RecipientType

			if participant.reference_doctype == "Customer":
				customer = frappe.get_doc("Customer", participant.reference_docname)
				mobile = get_customer_mobile_number(customer)
				name = customer.customer_name
				participant_type = "customer"

			elif participant.reference_doctype == "Employee":
				employee = frappe.get_doc("Employee", participant.reference_docname)
				mobile = get_employee_mobile_number(employee)
				name = employee.employee_name
				participant_type = "employee"

			if mobile and name:
				participants.append(
					{
						"name": name,
						"mobile": mobile,
						"type": participant_type,
						"doctype": participant.reference_doctype,
						"docname": participant.reference_docname,
					}
				)

		return participants

	except Exception as e:
		frappe.log_error(f"Erreur récupération participants événement {event_name}: {e}")
		return []

def get_customer_mobile_number(customer: "Document") -> str | None:
	"""Récupère le numéro mobile d'un client.

	Recherche le numéro mobile d'un client en vérifiant d'abord le champ
	mobile_no du Customer, puis en cherchant dans les Contacts liés.

	Args:
		customer: Document Customer Frappe.

	Returns:
		str | None: Numéro de téléphone mobile si trouvé, None sinon.
			Format du numéro tel que stocké (peut nécessiter normalisation).

	Example:
		>>> customer = frappe.get_doc("Customer", "CUST-001")
		>>> mobile = get_customer_mobile_number(customer)
		>>> if mobile:
		...     print(f"Mobile: {mobile}")

	Note:
		- Cherche d'abord dans customer.mobile_no
		- Si absent, cherche dans les Contacts via Dynamic Link
		- Retourne le premier numéro trouvé (mobile_no ou phone)
		- TODO: Convertir SQL en ORM (frappe.get_all)
	"""
	# Vérifier le champ mobile du customer
	if hasattr(customer, "mobile_no") and customer.mobile_no:
		return customer.mobile_no

	# Chercher dans les contacts
	try:
		# TODO: Convertir en frappe.get_all
		contacts = frappe.db.sql(
			"""
			SELECT mobile_no, phone
			FROM `tabContact`
			WHERE name IN (
				SELECT parent FROM `tabDynamic Link`
				WHERE link_doctype = 'Customer' AND link_name = %s
			)
			AND (mobile_no IS NOT NULL OR phone IS NOT NULL)
			LIMIT 1
		""",
			customer.name,
			as_dict=True,
		)

		if contacts:
			return contacts[0].mobile_no or contacts[0].phone
	except Exception as e:
		frappe.log_error(f"Erreur récupération mobile client {customer.name}: {e}")

	return None


def get_employee_mobile_number(employee: "Document") -> str | None:
	"""Récupère le numéro mobile d'un employé.

	Recherche le numéro mobile d'un employé en vérifiant plusieurs champs
	possibles dans l'ordre de priorité.

	Args:
		employee: Document Employee Frappe.

	Returns:
		str | None: Numéro de téléphone mobile si trouvé, None sinon.
			Format du numéro tel que stocké (peut nécessiter normalisation).

	Example:
		>>> employee = frappe.get_doc("Employee", "EMP-001")
		>>> mobile = get_employee_mobile_number(employee)
		>>> if mobile:
		...     print(f"Mobile: {mobile}")

	Note:
		Cherche dans l'ordre:
		1. employee.cell_number
		2. employee.personal_phone
		3. employee.phone
		Retourne le premier numéro trouvé.
	"""
	mobile_fields = ["cell_number", "personal_phone", "phone"]

	for field in mobile_fields:
		if hasattr(employee, field) and employee.get(field):
			return employee.get(field)

	return None

def log_event_reminder_sent(
	event_name: str,
	recipient_name: str,
	recipient_type: "RecipientType",
	mobile: str,
) -> None:
	"""Enregistre l'envoi d'un rappel d'événement dans les logs.

	Cette fonction crée une entrée de log pour tracer l'historique
	des rappels SMS envoyés.

	Args:
		event_name: Nom/ID de l'événement.
		recipient_name: Nom du destinataire.
		recipient_type: Type de destinataire ("customer" ou "employee").
		mobile: Numéro de téléphone mobile utilisé.

	Note:
		- Utilise le logger Frappe standard
		- Les erreurs de logging sont silencieuses (ne bloquent pas l'envoi)
		- TODO: Créer une table dédiée pour logs structurés (amélioration future)
	"""
	try:
		frappe.logger().info(
			f"Rappel événement envoyé - Événement: {event_name}, "
			f"Destinataire: {recipient_name} ({recipient_type}), Mobile: {mobile}"
		)

		# Optionnel: Créer un log structuré dans une table dédiée
		# create_reminder_log_entry(event_name, recipient_name, recipient_type, mobile)

	except Exception as e:
		frappe.log_error(f"Erreur logging rappel événement: {e}")

def process_pending_event_reminders() -> "SMSResult":
	"""Traite tous les rappels d'événements en attente.

	Fonction principale appelée par le scheduler pour envoyer les rappels SMS
	pour tous les événements qui correspondent aux critères configurés.

	Returns:
		SMSResult: Résultat du traitement avec:
			- success (bool): True si au moins un rappel envoyé avec succès
			- message (str): Résumé du traitement
			- sent (int): Nombre de rappels envoyés
			- failed (int): Nombre de rappels échoués

	Example:
		Appelé par le scheduler dans tasks.py:
		>>> result = process_pending_event_reminders()
		>>> print(result["message"])
		Traitement terminé: 5 envoyés, 0 échoués

	Note:
		- Vérifie d'abord si les rappels sont activés
		- Respecte les heures ouvrables si configuré
		- Met à jour les statistiques automatiquement
		- Filtre les destinataires selon la configuration
		  (send_to_customer_only, send_to_employee)
		- Les erreurs sont loggées mais ne bloquent pas le traitement
	"""
	try:
		reminder_settings = frappe.get_single("SMS Event Reminder")

		if not reminder_settings.enabled:
			return {"success": False, "message": "Rappels désactivés"}

		# Vérifier si c'est le bon moment
		if not reminder_settings.should_send_now():
			return {"success": False, "message": "Hors heures d'envoi"}

		events = get_events_requiring_reminders()
		total_sent = 0
		total_failed = 0

		for event_data in events:
			try:
				event_doc = frappe.get_doc("Event", event_data["name"])
				participants = get_event_participants_with_mobile(event_data["name"])

				for participant in participants:
					# Vérifier si on doit envoyer selon la configuration
					should_send = False

					if participant["type"] == "customer" and reminder_settings.send_to_customer_only:
						should_send = True
					elif participant["type"] == "employee" and reminder_settings.send_to_employee:
						should_send = True
					elif not reminder_settings.send_to_customer_only and not reminder_settings.send_to_employee:
						should_send = True  # Envoyer à tous par défaut

					if should_send:
						result = send_event_reminder_sms(
							event_doc, participant["mobile"], participant["name"], participant["type"]
						)

						if result and result.get("success"):
							total_sent += 1
						else:
							total_failed += 1

			except Exception as e:
				frappe.log_error(f"Erreur traitement événement {event_data['name']}: {e}")
				total_failed += 1

		# Mise à jour des statistiques
		if total_sent > 0 or total_failed > 0:
			update_reminder_statistics(total_sent, total_failed)

		return {
			"success": True,
			"message": f"Traitement terminé: {total_sent} envoyés, {total_failed} échoués",
			"sent": total_sent,
			"failed": total_failed,
		}

	except Exception as e:
		frappe.log_error(f"Erreur traitement rappels événements: {e}")
		return {"success": False, "message": str(e)}

def update_reminder_statistics(sent_count: int, failed_count: int) -> None:
	"""Met à jour les statistiques des rappels d'événements.

	Met à jour les compteurs globaux et journaliers des rappels SMS envoyés.

	Args:
		sent_count: Nombre de rappels envoyés avec succès.
		failed_count: Nombre de rappels échoués.

	Note:
		- Met à jour total_reminders_sent, failed_reminders_count
		- Met à jour last_check_time et last_reminder_sent
		- Réinitialise reminders_sent_today à minuit
		- Commit automatique des changements en base
		- Les erreurs sont loggées mais ne lèvent pas d'exception
	"""
	try:
		reminder_settings = frappe.get_single("SMS Event Reminder")
		now = datetime.now()

		# Mise à jour des compteurs
		reminder_settings.db_set(
			"total_reminders_sent", (reminder_settings.total_reminders_sent or 0) + sent_count
		)
		reminder_settings.db_set(
			"failed_reminders_count", (reminder_settings.failed_reminders_count or 0) + failed_count
		)
		reminder_settings.db_set("last_check_time", now)

		if sent_count > 0:
			reminder_settings.db_set("last_reminder_sent", now)

		# Compteur journalier
		today = now.date()
		last_check = reminder_settings.last_check_time.date() if reminder_settings.last_check_time else None

		if last_check != today:
			reminder_settings.db_set("reminders_sent_today", sent_count)
		else:
			reminder_settings.db_set(
				"reminders_sent_today", (reminder_settings.reminders_sent_today or 0) + sent_count
			)

		frappe.db.commit()

	except Exception as e:
		frappe.log_error(f"Erreur mise à jour statistiques rappels: {e}")

# === FONCTIONS D'API POUR L'INTERFACE ===


@frappe.whitelist()
def get_pending_events() -> dict[str, Any]:
	"""API pour récupérer les événements en attente de rappel.

	Endpoint API pour l'interface utilisateur pour afficher les événements
	qui nécessitent un rappel SMS.

	Returns:
		dict: Résultat avec:
			- success (bool): True si requête réussie
			- events (list): Liste des événements en attente
			- count (int): Nombre d'événements
			ou
			- success (bool): False si erreur
			- message (str): Message d'erreur

	Example:
		Appel depuis le frontend JavaScript:
		```javascript
		frappe.call({
		    method: 'ovh_sms_integration.utils.sms_utils.get_pending_events',
		    callback: function(r) {
		        console.log(r.message.count + ' événements en attente');
		    }
		});
		```

	Note:
		- Nécessite @frappe.whitelist() pour être accessible via HTTP
		- Pas de permissions spéciales requises
	"""
	try:
		events = get_events_requiring_reminders()
		return {"success": True, "events": events, "count": len(events)}
	except Exception as e:
		frappe.log_error(f"Erreur API pending events: {e}")
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def manual_send_event_reminder(event_name: str, test_mode: bool = False) -> dict[str, Any]:
	"""Envoie manuellement un rappel pour un événement spécifique.

	Endpoint API pour permettre l'envoi manuel de rappels depuis l'interface.
	Peut être utilisé en mode test sans envoyer réellement les SMS.

	Args:
		event_name: Nom/ID de l'événement.
		test_mode: Si True, simule l'envoi sans envoyer réellement.
			Par défaut False.

	Returns:
		dict: Résultat avec:
			- success (bool): True si au moins un rappel envoyé
			- message (str): Résumé des envois
			- details (list): Liste détaillée par participant
			ou
			- success (bool): False si erreur
			- message (str): Message d'erreur

	Example:
		Test d'envoi depuis le frontend:
		```javascript
		frappe.call({
		    method: 'ovh_sms_integration.utils.sms_utils.manual_send_event_reminder',
		    args: {event_name: 'EVT-001', test_mode: true},
		    callback: function(r) {
		        frappe.msgprint(r.message.message);
		    }
		});
		```

	Note:
		- Nécessite @frappe.whitelist() pour être accessible via HTTP
		- Le mode test permet de vérifier les participants sans consommer de crédits SMS
		- Retourne les détails pour chaque participant
	"""
	try:
		event_doc = frappe.get_doc("Event", event_name)
		participants = get_event_participants_with_mobile(event_name)

		if not participants:
			return {"success": False, "message": "Aucun participant avec mobile trouvé"}

		results = []
		for participant in participants:
			if not test_mode:
				result = send_event_reminder_sms(
					event_doc, participant["mobile"], participant["name"], participant["type"]
				)
			else:
				result = {"success": True, "message": "Mode test - SMS non envoyé"}

			results.append(
				{
					"participant": participant["name"],
					"type": participant["type"],
					"mobile": participant["mobile"],
					"result": result,
				}
			)

		success_count = sum(1 for r in results if r["result"].get("success", False))

		return {
			"success": success_count > 0,
			"message": f"{success_count}/{len(results)} rappels envoyés",
			"details": results,
		}

	except Exception as e:
		frappe.log_error(f"Erreur envoi rappel manuel: {e}")
		return {"success": False, "message": str(e)}

# === ANCIENNES FONCTIONS CONSERVÉES ===


def send_daily_reminders() -> None:
	"""Envoie les rappels quotidiens.

	Note:
		TODO: Implémentation à compléter pour les rappels quotidiens.
	"""
	# Implémentation des rappels quotidiens
	pass


def send_weekly_reports() -> None:
	"""Envoie les rapports hebdomadaires.

	Note:
		TODO: Implémentation à compléter pour les rapports hebdomadaires.
	"""
	# Implémentation des rapports hebdomadaires
	pass


@frappe.whitelist()
def test_ovh_connection() -> dict[str, Any]:
	"""Test la connexion à l'API OVH SMS.

	Endpoint API pour tester la configuration OVH depuis l'interface.

	Returns:
		dict: Résultat du test avec success (bool) et message (str).

	Example:
		```javascript
		frappe.call({
		    method: 'ovh_sms_integration.utils.sms_utils.test_ovh_connection',
		    callback: function(r) {
		        frappe.msgprint(r.message.message);
		    }
		});
		```

	Note:
		Délègue le test à la méthode test_connection() du doctype OVH SMS Settings.
	"""
	settings = get_ovh_sms_settings()
	if not settings:
		return {"success": False, "message": "OVH SMS non configuré"}

	return settings.test_connection()


@frappe.whitelist()
def send_manual_sms(
	message: str,
	receivers: str | list[str],
	sender: str | None = None,
) -> list[dict[str, Any]]:
	"""Envoie un SMS manuel à un ou plusieurs destinataires.

	Endpoint API pour l'envoi manuel de SMS depuis l'interface utilisateur.

	Args:
		message: Contenu du SMS à envoyer.
		receivers: Numéro(s) de téléphone destinataire(s).
			Peut être une chaîne unique ou une liste.
		sender: Nom de l'expéditeur (optionnel).

	Returns:
		list[dict]: Liste des résultats pour chaque destinataire avec:
			- receiver (str): Numéro du destinataire
			- success (bool): True si envoi réussi
			- result (SMSResult): Résultat détaillé de l'envoi

	Example:
		Envoi depuis le frontend:
		```javascript
		frappe.call({
		    method: 'ovh_sms_integration.utils.sms_utils.send_manual_sms',
		    args: {
		        message: 'Test SMS',
		        receivers: ['+33612345678', '+33698765432']
		    },
		    callback: function(r) {
		        console.log(r.message);
		    }
		});
		```

	Note:
		- Accepte un seul numéro (string) ou plusieurs (list)
		- Chaque envoi est indépendant (continue même si un échoue)
	"""
	if isinstance(receivers, str):
		receivers = [receivers]

	results = []
	for receiver in receivers:
		result = send_sms(message, receiver, sender)
		results.append({"receiver": receiver, "success": result is not None, "result": result})

	return results


@frappe.whitelist()
def get_sms_balance() -> dict[str, Any] | None:
	"""Récupère le solde SMS du compte OVH.

	Endpoint API pour afficher le crédit SMS restant dans l'interface.

	Returns:
		dict | None: Informations sur le solde ou None si non configuré.

	Example:
		```javascript
		frappe.call({
		    method: 'ovh_sms_integration.utils.sms_utils.get_sms_balance',
		    callback: function(r) {
		        if (r.message) {
		            console.log('Solde: ' + r.message.credits);
		        }
		    }
		});
		```

	Note:
		Délègue la récupération à la méthode get_sms_balance() du doctype OVH SMS Settings.
	"""
	settings = get_ovh_sms_settings()
	if not settings:
		return None

	return settings.get_sms_balance()


def format_sms_message(template: str, doc: "Document") -> str:
	"""Fonction Jinja pour formater les messages SMS avec un document.

	Utilitaire pour formater un template avec toutes les données d'un document.

	Args:
		template: Template Jinja2 du message.
		doc: Document Frappe contenant les données.

	Returns:
		str: Message formaté avec les données du document.
			Si template ou doc est None, retourne le template original.

	Example:
		>>> template = "Bonjour {{customer_name}}, votre commande {{name}} est prête"
		>>> so = frappe.get_doc("Sales Order", "SO-001")
		>>> message = format_sms_message(template, so)

	Note:
		Utilise doc.as_dict() pour convertir le document en contexte.
	"""
	if not template or not doc:
		return template

	context = doc.as_dict()
	return format_message_template(template, context)
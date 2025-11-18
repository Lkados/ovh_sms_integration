# -*- coding: utf-8 -*-
"""SMS Event Reminder doctype.

Ce module gère les rappels SMS automatiques pour les événements.
Il fournit les fonctionnalités de:
- Configuration des rappels par type d'événement
- Envoi de rappels multiples programmables
- Templates personnalisables par type de destinataire
- Filtrage par heures ouvrables et week-ends
- Parsing de données structurées dans les descriptions d'événements
- Statistiques et historique des rappels
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import frappe
from frappe import _
from frappe.model.document import Document
from jinja2 import Template

if TYPE_CHECKING:
	from ovh_sms_integration.types import ParsedEventData

class SMSEventReminder(Document):
	"""DocType de configuration pour les rappels SMS d'événements.

	Gère la configuration et l'envoi automatique de rappels SMS pour
	les événements Frappe selon des critères configurables.

	Attributes:
		enabled (bool): Active/désactive les rappels
		event_type_filter (str): Type d'événement à surveiller
		reminder_hours_before (float): Heures avant l'événement pour le rappel
		enable_multiple_reminders (bool): Active les rappels multiples
		reminder_times (str): Liste des heures de rappel (CSV)
		customer_template (str): Template pour clients
		employee_template (str): Template pour employés
		default_template (str): Template par défaut
		reminder_message_template (str): Template de message
		business_hours_only (bool): Envoyer uniquement pendant heures ouvrables
		business_start_time (Time): Heure de début des heures ouvrables
		business_end_time (Time): Heure de fin des heures ouvrables
		exclude_weekends (bool): Exclure les week-ends
	"""

	def validate(self) -> None:
		"""Valide la configuration avant sauvegarde.

		Raises:
			frappe.ValidationError: Si des champs requis sont manquants.
			frappe.ValidationError: Si reminder_hours_before <= 0.
			frappe.ValidationError: Si reminder_times est invalide.

		Note:
			- Vérifie event_type_filter si enabled
			- Vérifie reminder_hours_before > 0
			- Valide le format CSV de reminder_times
			- Vérifie que toutes les heures sont positives
		"""
		if self.enabled:
			if not self.event_type_filter:
				frappe.throw(_("Type d'événement à surveiller est requis"))
			
			if self.reminder_hours_before <= 0:
				frappe.throw(_("Les heures avant l'événement doivent être positives"))
			
			if self.enable_multiple_reminders and not self.reminder_times:
				frappe.throw(_("Heures de rappel requises pour les rappels multiples"))
			
			# Validation des heures de rappel multiples
			if self.enable_multiple_reminders and self.reminder_times:
				try:
					times = [float(x.strip()) for x in self.reminder_times.split(',')]
					if any(t <= 0 for t in times):
						frappe.throw(_("Toutes les heures de rappel doivent être positives"))
				except ValueError:
					frappe.throw(_("Format invalide pour les heures de rappel (ex: 24,2,0.5)"))

	def get_reminder_times(self) -> list[float]:
		"""Retourne la liste des heures de rappel configurées.

		Parse le champ reminder_times (format CSV) et retourne une liste
		de valeurs float représentant les heures avant l'événement.

		Returns:
			list[float]: Liste des heures de rappel. Si reminder_times
				est invalide ou non défini, retourne [reminder_hours_before].

		Example:
			>>> reminder = frappe.get_doc("SMS Event Reminder", "...")
			>>> reminder.reminder_times = "24,2,0.5"
			>>> reminder.get_reminder_times()
			[24.0, 2.0, 0.5]

		Note:
			- Fallback sur reminder_hours_before si parsing échoue
			- Les erreurs de parsing sont loggées
			- Format attendu: "24,2,0.5" (heures séparées par virgules)
		"""
		if self.enable_multiple_reminders and self.reminder_times:
			try:
				return [float(x.strip()) for x in self.reminder_times.split(',')]
			except ValueError:
				frappe.log_error("Format invalide pour reminder_times")
				return [float(self.reminder_hours_before)]
		else:
			return [float(self.reminder_hours_before)]

	def get_message_template(self, recipient_type: str = "customer") -> str:
		"""Retourne le template de message approprié selon le type de destinataire.

		Sélectionne le template en fonction du type de destinataire avec
		fallback sur des templates par défaut.

		Args:
			recipient_type: Type de destinataire ("customer" ou "employee").
				Par défaut "customer".

		Returns:
			str: Template Jinja2 pour le message SMS.

		Example:
			>>> reminder = frappe.get_doc("SMS Event Reminder", "...")
			>>> template = reminder.get_message_template("customer")
			>>> # Retourne customer_template si défini, sinon default_template

		Note:
			- Ordre de priorité: customer_template > employee_template
			  > default_template > reminder_message_template
			- Tous les templates supportent Jinja2
		"""
		if recipient_type == "customer" and self.customer_template:
			return self.customer_template
		elif recipient_type == "employee" and self.employee_template:
			return self.employee_template
		elif self.default_template:
			return self.default_template
		else:
			return self.reminder_message_template

	def should_send_now(self) -> bool:
		"""Vérifie si on peut envoyer des SMS maintenant selon les contraintes.

		Applique les filtres configurés (heures ouvrables, week-ends) pour
		déterminer si l'envoi est autorisé à l'instant présent.

		Returns:
			bool: True si l'envoi est autorisé maintenant, False sinon.

		Example:
			>>> reminder = frappe.get_doc("SMS Event Reminder", "...")
			>>> reminder.business_hours_only = True
			>>> reminder.business_start_time = "09:00:00"
			>>> reminder.should_send_now()
			False  # Si appelé à 08:00

		Note:
			- Vérifie business_hours_only avec business_start_time/end_time
			- Vérifie exclude_weekends (samedi=5, dimanche=6)
			- Retourne True si aucun filtre n'est activé
		"""
		now = datetime.now()
		
		# Vérification des heures ouvrables
		if self.business_hours_only:
			current_time = now.time()
			if (self.business_start_time and current_time < self.business_start_time or
				self.business_end_time and current_time > self.business_end_time):
				return False
		
		# Vérification des week-ends
		if self.exclude_weekends and now.weekday() >= 5:  # 5=samedi, 6=dimanche
			return False
		
		return True

	def parse_event_data(self, description: str | None) -> "ParsedEventData":
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
			>>> data = reminder.parse_event_data(desc)
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
			data = {}
			import re
			
			# Patterns pour extraire les informations
			patterns = {
				'client': r'\*\*Client:\*\*\s*([^\n\r*]+)',
				'reference': r'\*\*Référence:\*\*\s*([^\n\r*]+)',
				'type': r'\*\*Type:\*\*\s*([^\n\r*]+)',
				'article': r'\*\*Article:\*\*\s*([^\n\r*]+)',
				'tel_client': r'\*\*Tél client:\*\*\s*([^\n\r*]+)',
				'email_client': r'\*\*Email client:\*\*\s*([^\n\r*]+)',
				'appareil': r'\*\*Appareil:\*\*\s*([^\n\r*]+)',
				'camion_requis': r'\*\*Camion requis:\*\*\s*([^\n\r*]+)'
			}
			
			# Extraction avec markdown
			for key, pattern in patterns.items():
				match = re.search(pattern, description)
				if match:
					data[key] = match.group(1).strip()
			
			# Si pas trouvé avec markdown, essayer sans
			if not data:
				patterns_simple = {
					'client': r'Client:\s*([^\n\r]+)',
					'reference': r'Référence:\s*([^\n\r]+)',
					'type': r'Type:\s*([^\n\r]+)',
					'article': r'Article:\s*([^\n\r]+)',
					'tel_client': r'Tél client:\s*([^\n\r]+)',
					'email_client': r'Email client:\s*([^\n\r]+)',
					'appareil': r'Appareil:\s*([^\n\r]+)',
					'camion_requis': r'Camion requis:\s*([^\n\r]+)'
				}
				
				for key, pattern in patterns_simple.items():
					match = re.search(pattern, description)
					if match:
						data[key] = match.group(1).strip()
			
			return data
			
		except Exception as e:
			frappe.log_error(f"Erreur parsing données événement: {e}")
			return {}

	def format_message(
		self,
		template: str,
		event_doc: Any,
		customer_name: str | None = None,
		employee_name: str | None = None
	) -> str:
		"""Formate le message avec les données de l'événement.

		Rend le template Jinja2 avec toutes les variables d'événement
		disponibles, incluant les données parsées de la description.

		Args:
			template: Template Jinja2 du message.
			event_doc: Document Event Frappe.
			customer_name: Nom du client destinataire. Par défaut None.
			employee_name: Nom de l'employé destinataire. Par défaut None.

		Returns:
			str: Message formaté prêt à être envoyé. En cas d'erreur,
				retourne le template original.

		Example:
			>>> event = frappe.get_doc("Event", "EVT-001")
			>>> template = "Rappel: {{subject}} le {{start_date}} à {{start_time}}"
			>>> msg = reminder.format_message(template, event)
			>>> # "Rappel: RDV Client le 15/01/2025 à 14:00"

		Note:
			- Variables disponibles: subject, description, event_name,
			  start_date, start_time, location, customer_name, employee_name,
			  duration, + toutes les données parsées (client, reference, etc.)
			- Dates au format DD/MM/YYYY, heures au format HH:MM
			- Les erreurs sont loggées et le template original est retourné
		"""
		try:
			# Parse des données structurées
			event_data = self.parse_event_data(event_doc.description)
			
			# Préparation du contexte de base
			context = {
				'subject': event_doc.subject or '',
				'description': event_doc.description or '',
				'event_name': event_doc.name,
				'start_date': event_doc.starts_on.strftime('%d/%m/%Y') if event_doc.starts_on else '',
				'start_time': event_doc.starts_on.strftime('%H:%M') if event_doc.starts_on else '',
				'location': getattr(event_doc, 'location', '') or '',
				'customer_name': customer_name or '',
				'employee_name': employee_name or ''
			}
			
			# Ajout des données parsées
			context.update({
				'client': event_data.get('client', ''),
				'reference': event_data.get('reference', ''),
				'type': event_data.get('type', ''),
				'article': event_data.get('article', ''),
				'tel_client': event_data.get('tel_client', ''),
				'email_client': event_data.get('email_client', ''),
				'appareil': event_data.get('appareil', ''),
				'camion_requis': event_data.get('camion_requis', '')
			})
			
			# Calcul de la durée si disponible
			if event_doc.starts_on and event_doc.ends_on:
				duration = (event_doc.ends_on - event_doc.starts_on).total_seconds() / 60
				context['duration'] = int(duration)
			else:
				context['duration'] = ''
			
			# Formatage avec Jinja2
			template_obj = Template(template)
			return template_obj.render(**context)
			
		except Exception as e:
			frappe.log_error(f"Erreur formatage message rappel: {e}")
			return template  # Retourne le template original en cas d'erreur

	def extract_event_type_from_description(self, description: str | None) -> str | None:
		"""Extrait le type d'événement depuis la description structurée.

		Parse la description pour extraire le champ "Type:" qui indique
		le type d'événement (Entretien, Livraison, etc.).

		Args:
			description: Description de l'événement avec données structurées.

		Returns:
			str | None: Type d'événement extrait, ou None si non trouvé.

		Example:
			>>> desc = "**Type:** Entretien\\n**Client:** John"
			>>> reminder.extract_event_type_from_description(desc)
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
			# Recherche du pattern "Type:" dans la description
			import re
			type_match = re.search(r'\*\*Type:\*\*\s*([^\n\r*]+)', description)
			if type_match:
				return type_match.group(1).strip()
			
			# Essayer aussi sans les ** (markdown)
			type_match = re.search(r'Type:\s*([^\n\r]+)', description)
			if type_match:
				return type_match.group(1).strip()
			
			return None
		except Exception as e:
			frappe.log_error(f"Erreur extraction type événement: {e}")
			return None

	def get_events_for_reminder(self) -> list[dict[str, Any]]:
		"""Récupère les événements nécessitant un rappel.

		Recherche les événements dans les fenêtres de temps configurées
		et filtre selon les critères (type, durée, all_day, etc.).

		Returns:
			list[dict[str, Any]]: Liste des événements avec leurs données.
				Chaque dict contient: name, subject, description, starts_on,
				ends_on, event_participants, location.

		Example:
			>>> reminder = frappe.get_doc("SMS Event Reminder", "...")
			>>> reminder.reminder_times = "24,2"
			>>> events = reminder.get_events_for_reminder()
			>>> len(events)
			5  # 5 événements à rappeler

		Note:
			- Utilise des fenêtres de ±30min autour de chaque reminder_time
			- Filtre par event_type_filter (extrait de la description)
			- Applique skip_past_events, skip_all_day_events, minimum_event_duration
			- Les erreurs retournent une liste vide et sont loggées
		"""
		if not self.enabled:
			return []

		try:
			# Calcul des plages de temps pour les rappels
			reminder_times = self.get_reminder_times()
			now = datetime.now()

			# Construction des filtres de temps pour l'ORM
			time_filters = []
			for hours_before in reminder_times:
				start_time = now + timedelta(hours=hours_before-0.5)  # Marge de 30min
				end_time = now + timedelta(hours=hours_before+0.5)
				time_filters.append(["starts_on", "between", [start_time, end_time]])

			# Construction des filtres de base
			base_filters = {
				"docstatus": 1
			}

			if self.skip_past_events:
				base_filters["starts_on"] = [">", now]

			if self.skip_all_day_events:
				base_filters["all_day"] = 0

			# Récupération de TOUS les événements dans les plages horaires (ORM Frappe)
			# Note: OR conditions sur starts_on nécessitent plusieurs requêtes
			all_events = []
			for time_filter in time_filters:
				filters = base_filters.copy()
				filters["starts_on"] = time_filter[2]  # Extract [start, end] from filter

				events = frappe.get_all(
					"Event",
					filters=filters,
					fields=["name", "subject", "description", "starts_on", "ends_on",
						   "event_participants", "location"]
				)
				all_events.extend(events)
			
			# Filtrage par type extrait de la description
			filtered_events = []
			event_types_to_filter = [t.strip() for t in self.event_type_filter.split(',')]
			
			for event in all_events:
				# Méthode 1: Extraire le type depuis la description structurée
				event_type = self.extract_event_type_from_description(event.description)
				
				# Méthode 2: Fallback - chercher dans le titre si pas trouvé dans description
				if not event_type:
					for filter_type in event_types_to_filter:
						if filter_type.lower() in (event.subject or '').lower():
							event_type = filter_type
							break
				
				# Vérifier si le type correspond aux filtres
				if event_type:
					for filter_type in event_types_to_filter:
						if filter_type.lower() in event_type.lower():
							filtered_events.append(event)
							break
			
			# Filtrage par durée minimum
			if self.minimum_event_duration > 0:
				final_events = []
				for event in filtered_events:
					if event.ends_on and event.starts_on:
						duration = (event.ends_on - event.starts_on).total_seconds() / 60
						if duration >= self.minimum_event_duration:
							final_events.append(event)
				filtered_events = final_events
			
			return filtered_events
			
		except Exception as e:
			frappe.log_error(f"Erreur récupération événements: {e}")
			return []

	def get_event_contacts(self, event: Any) -> dict[str, list[dict[str, Any]]]:
		"""Récupère les contacts (clients et employés) d'un événement.

		Extrait tous les participants de l'événement et récupère leurs
		numéros de téléphone mobile.

		Args:
			event: Document Event ou dict with 'name' key.

		Returns:
			dict[str, list[dict[str, Any]]]: Contacts groupés par type:
				- customers: Liste de dicts {name, mobile, doc}
				- employees: Liste de dicts {name, mobile, doc}

		Example:
			>>> event = frappe.get_doc("Event", "EVT-001")
			>>> contacts = reminder.get_event_contacts(event)
			>>> contacts["customers"]
			[{'name': 'ACME Corp', 'mobile': '+33612345678', 'doc': ...}]

		Note:
			- TODO: Convertir SQL en ORM Frappe
			- Utilise get_customer_mobile() et get_employee_mobile()
			- Ignore les participants sans numéro de téléphone
			- Les erreurs sont loggées et retournent des listes vides
		"""
		contacts = {
			'customers': [],
			'employees': []
		}

		try:
			# Récupération des participants (ORM Frappe)
			participants = frappe.get_all(
				"Event Participants",
				filters={"parent": event.name},
				fields=["reference_doctype", "reference_docname"]
			)
			
			for participant in participants:
				if participant.reference_doctype == "Customer":
					# Récupération du mobile du client
					customer = frappe.get_doc("Customer", participant.reference_docname)
					mobile = self.get_customer_mobile(customer)
					if mobile:
						contacts['customers'].append({
							'name': customer.customer_name,
							'mobile': mobile,
							'doc': customer
						})
				
				elif participant.reference_doctype == "Employee":
					# Récupération du mobile de l'employé
					employee = frappe.get_doc("Employee", participant.reference_docname)
					mobile = self.get_employee_mobile(employee)
					if mobile:
						contacts['employees'].append({
							'name': employee.employee_name,
							'mobile': mobile,
							'doc': employee
						})
		
		except Exception as e:
			frappe.log_error(f"Erreur récupération contacts événement {event.name}: {e}")
		
		return contacts

	def get_customer_mobile(self, customer: Any) -> str | None:
		"""Récupère le numéro mobile d'un client.

		Recherche le numéro de téléphone mobile dans le document Customer
		puis dans les contacts liés si non trouvé.

		Args:
			customer: Document Customer Frappe.

		Returns:
			str | None: Numéro de téléphone mobile, ou None si non trouvé.

		Example:
			>>> customer = frappe.get_doc("Customer", "CUST-001")
			>>> mobile = reminder.get_customer_mobile(customer)
			>>> mobile
			'+33612345678'

		Note:
			- Vérifie d'abord customer.mobile_no
			- Fallback sur Contact via Dynamic Link
			- Préfère mobile_no à phone
			- Retourne None si aucun numéro trouvé
		"""
		# Vérifier d'abord sur le document Customer
		if hasattr(customer, 'mobile_no') and customer.mobile_no:
			return customer.mobile_no

		# Chercher dans les contacts liés (ORM Frappe)
		try:
			# Récupérer les Dynamic Links pour ce client
			dynamic_links = frappe.get_all(
				"Dynamic Link",
				filters={
					"link_doctype": "Customer",
					"link_name": customer.name
				},
				fields=["parent"]
			)

			if not dynamic_links:
				return None

			# Récupérer les contacts avec numéro de téléphone
			contact_names = [link.parent for link in dynamic_links]
			contacts = frappe.get_all(
				"Contact",
				filters=[
					["name", "in", contact_names],
					["mobile_no", "is", "set"]
				],
				fields=["mobile_no", "phone"],
				limit=1
			)

			# Fallback si pas de mobile_no mais un phone
			if not contacts:
				contacts = frappe.get_all(
					"Contact",
					filters=[
						["name", "in", contact_names],
						["phone", "is", "set"]
					],
					fields=["mobile_no", "phone"],
					limit=1
				)

			if contacts:
				return contacts[0].mobile_no or contacts[0].phone
		except Exception as e:
			frappe.log_error(f"Erreur récupération mobile client {customer.name}: {e}")
		
		return None

	def get_employee_mobile(self, employee: Any) -> str | None:
		"""Récupère le numéro mobile d'un employé.

		Recherche le numéro de téléphone mobile dans le document Employee
		en testant plusieurs champs possibles.

		Args:
			employee: Document Employee Frappe.

		Returns:
			str | None: Numéro de téléphone mobile, ou None si non trouvé.

		Example:
			>>> employee = frappe.get_doc("Employee", "EMP-001")
			>>> mobile = reminder.get_employee_mobile(employee)
			>>> mobile
			'+33612345678'

		Note:
			- Teste dans l'ordre: cell_number, personal_phone, phone
			- Retourne le premier champ non vide trouvé
			- Retourne None si aucun numéro disponible
		"""
		mobile_fields = ['cell_number', 'personal_phone', 'phone']
		
		for field in mobile_fields:
			if hasattr(employee, field) and employee.get(field):
				return employee.get(field)
		
		return None

	def send_event_reminders(self) -> None:
		"""Envoie les rappels pour tous les événements éligibles.

		Méthode principale pour traiter l'envoi de tous les rappels SMS.
		Récupère les événements, les contacts, formate et envoie les messages.

		Note:
			- Vérifie enabled et should_send_now() avant envoi
			- Utilise is_reminder_already_sent() pour éviter les doublons
			- Envoie aux customers et/ou employees selon configuration
			- Met à jour les statistiques automatiquement
			- Loggue tous les succès et échecs
			- Les erreurs sont loggées mais ne bloquent pas les autres envois
		"""
		if not self.enabled or not self.should_send_now():
			return
		
		try:
			events = self.get_events_for_reminder()
			sent_count = 0
			failed_count = 0
			
			for event in events:
				# Vérifier si le rappel a déjà été envoyé
				if self.is_reminder_already_sent(event.name):
					continue
				
				contacts = self.get_event_contacts(event)
				event_doc = frappe.get_doc("Event", event.name)
				
				# Envoi aux clients
				if self.send_to_customer_only or not self.send_to_employee:
					for customer in contacts['customers']:
						try:
							template = self.get_message_template("customer")
							message = self.format_message(
								template, event_doc, 
								customer_name=customer['name']
							)
							
							result = self.send_sms_reminder(message, customer['mobile'])
							if result and result.get('success'):
								sent_count += 1
								self.log_reminder_sent(event.name, customer['name'], "customer")
							else:
								failed_count += 1
								
						except Exception as e:
							frappe.log_error(f"Erreur envoi rappel client {customer['name']}: {e}")
							failed_count += 1
				
				# Envoi aux employés
				if self.send_to_employee:
					for employee in contacts['employees']:
						try:
							template = self.get_message_template("employee")
							message = self.format_message(
								template, event_doc, 
								employee_name=employee['name']
							)
							
							result = self.send_sms_reminder(message, employee['mobile'])
							if result and result.get('success'):
								sent_count += 1
								self.log_reminder_sent(event.name, employee['name'], "employee")
							else:
								failed_count += 1
								
						except Exception as e:
							frappe.log_error(f"Erreur envoi rappel employé {employee['name']}: {e}")
							failed_count += 1
			
			# Mise à jour des statistiques
			self.update_statistics(sent_count, failed_count)
			
			if sent_count > 0 or failed_count > 0:
				frappe.logger().info(f"Rappels événements envoyés: {sent_count}, échoués: {failed_count}")
		
		except Exception as e:
			frappe.log_error(f"Erreur envoi rappels événements: {e}")

	def get_best_sender(self) -> str:
		"""Retourne le meilleur expéditeur disponible depuis OVH SMS Settings.

		Délègue la sélection de l'expéditeur à OVH SMS Settings.

		Returns:
			str: Nom de l'expéditeur SMS à utiliser. Retourne "ERPNext"
				en fallback si erreur ou si OVH SMS non activé.

		Note:
			- Délègue à sms_settings.get_best_sender()
			- Fallback "ERPNext" si OVH SMS désactivé
			- Les erreurs sont loggées et retournent le fallback
		"""
		try:
			sms_settings = frappe.get_single('OVH SMS Settings')
			if not sms_settings.enabled:
				return "ERPNext"  # Fallback
			
			return sms_settings.get_best_sender()
		except Exception as e:
			frappe.log_error(f"Erreur récupération expéditeur: {e}")
			return "ERPNext"  # Fallback

	def send_sms_reminder(self, message: str, mobile: str) -> dict[str, Any]:
		"""Envoie un SMS de rappel via l'intégration OVH.

		Délègue l'envoi réel à OVH SMS Settings.

		Args:
			message: Contenu du SMS formaté.
			mobile: Numéro de téléphone mobile du destinataire.

		Returns:
			dict[str, Any]: Résultat de l'envoi avec success et message.

		Note:
			- Délègue à sms_settings.send_sms()
			- Retourne {"success": False} si OVH SMS désactivé
			- Les erreurs sont loggées et retournent un dict d'échec
		"""
		try:
			sms_settings = frappe.get_single('OVH SMS Settings')
			if not sms_settings.enabled:
				return {"success": False, "message": "OVH SMS non activé"}
			
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

		Note:
			- TODO: Implémenter la vérification dans les logs
			- Actuellement retourne toujours False (pas de déduplication)
			- Peut être implémenté avec un doctype de log séparé
		"""
		# Vérification dans les logs (optionnel - peut être implémenté selon les besoins)
		return False

	def log_reminder_sent(self, event_name: str, recipient_name: str, recipient_type: str) -> None:
		"""Log l'envoi d'un rappel.

		Enregistre les informations sur l'envoi d'un rappel dans les logs.

		Args:
			event_name: Nom/ID de l'événement.
			recipient_name: Nom du destinataire.
			recipient_type: Type de destinataire ("customer" ou "employee").

		Note:
			- TODO: Implémenter la persistance dans un doctype de log
			- Actuellement loggue uniquement dans frappe.logger
			- Utile pour le suivi et les statistiques
			- Les erreurs sont ignorées (logging non bloquant)
		"""
		try:
			# Créer un log d'envoi si nécessaire
			frappe.logger().info(f"Rappel envoyé - Événement: {event_name}, Destinataire: {recipient_name} ({recipient_type})")
		except Exception as e:
			frappe.log_error(f"Erreur logging rappel: {e}")

	def update_statistics(self, sent_count: int, failed_count: int) -> None:
		"""Met à jour les statistiques d'envoi.

		Met à jour les compteurs de statistiques dans le document après
		un batch d'envois de rappels.

		Args:
			sent_count: Nombre de SMS envoyés avec succès.
			failed_count: Nombre de SMS échoués.

		Note:
			- Utilise db_set() pour mise à jour sans déclenchement de hooks
			- Met à jour: total_reminders_sent, failed_reminders_count,
			  last_check_time, next_check_time, last_reminder_sent
			- Reset reminders_sent_today à minuit
			- Planifie next_check_time à +1h
			- Les erreurs sont loggées mais ne lèvent pas d'exception
		"""
		try:
			now = datetime.now()
			
			# Mise à jour des compteurs
			self.db_set('total_reminders_sent', (self.total_reminders_sent or 0) + sent_count)
			self.db_set('failed_reminders_count', (self.failed_reminders_count or 0) + failed_count)
			self.db_set('last_check_time', now)
			self.db_set('next_check_time', now + timedelta(hours=1))  # Prochaine vérification dans 1h
			
			if sent_count > 0:
				self.db_set('last_reminder_sent', now)
			
			# Compteur journalier (reset à minuit)
			today = now.date()
			last_check = self.last_check_time.date() if self.last_check_time else None
			
			if last_check != today:
				self.db_set('reminders_sent_today', sent_count)
			else:
				self.db_set('reminders_sent_today', (self.reminders_sent_today or 0) + sent_count)
		
		except Exception as e:
			frappe.log_error(f"Erreur mise à jour statistiques: {e}")


# Méthodes globales pour l'API et les tâches planifiées

@frappe.whitelist()
def send_test_reminder() -> dict[str, Any]:
	"""API endpoint pour envoyer un rappel de test.

	Fonction whitelistée pour tester l'envoi de rappels SMS avec
	un événement et des numéros de test configurés.

	Returns:
		dict[str, Any]: Résultat du test avec:
			- success (bool): État global du test
			- message (str): Message de synthèse
			- details (list): Détails par destinataire testé

	Example:
		>>> # Depuis JavaScript
		>>> frappe.call({
		...     method: "ovh_sms_integration...send_test_reminder",
		...     callback: function(r) {
		...         console.log(r.message.details);
		...     }
		... })

	Note:
		- Nécessite test_event, test_customer_mobile ou test_employee_mobile
		- Met à jour last_test_result dans le document
		- Teste les templates customer et employee séparément
		- Les erreurs sont loggées et retournent success: False
	"""
	try:
		settings = frappe.get_single('SMS Event Reminder')
		
		if not settings.enabled:
			return {
				"success": False,
				"message": "Les rappels d'événements ne sont pas activés"
			}
		
		if not settings.test_event:
			return {
				"success": False,
				"message": "Aucun événement de test sélectionné"
			}
		
		# Récupération de l'événement de test
		event = frappe.get_doc("Event", settings.test_event)
		
		results = []
		
		# Test client
		if settings.test_customer_mobile:
			template = settings.get_message_template("customer")
			message = settings.format_message(template, event, customer_name="Client Test")
			
			result = settings.send_sms_reminder(message, settings.test_customer_mobile)
			results.append({
				"recipient": "Client",
				"mobile": settings.test_customer_mobile,
				"message": message,
				"result": result
			})
		
		# Test employé
		if settings.test_employee_mobile:
			template = settings.get_message_template("employee")
			message = settings.format_message(template, event, employee_name="Employé Test")
			
			result = settings.send_sms_reminder(message, settings.test_employee_mobile)
			results.append({
				"recipient": "Employé",
				"mobile": settings.test_employee_mobile,
				"message": message,
				"result": result
			})
		
		if not results:
			return {
				"success": False,
				"message": "Aucun numéro de test configuré"
			}
		
		# Mise à jour du résultat du test
		result_text = "\n".join([
			f"{r['recipient']} ({r['mobile']}): {'✓' if r['result'].get('success') else '✗'} - {r['result'].get('message', '')}"
			for r in results
		])
		
		settings.db_set('last_test_result', result_text)
		
		success_count = sum(1 for r in results if r['result'].get('success'))
		
		return {
			"success": success_count > 0,
			"message": f"{success_count}/{len(results)} rappels de test envoyés avec succès",
			"details": results
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur envoi rappel de test: {e}")
		return {
			"success": False,
			"message": f"Erreur: {str(e)}"
		}

def process_event_reminders() -> None:
	"""Fonction appelée par le scheduler pour traiter les rappels.

	Point d'entrée pour le traitement automatique des rappels d'événements
	via le Frappe scheduler.

	Note:
		- Appelée périodiquement par le scheduler (configuré dans hooks.py)
		- Vérifie que les rappels sont activés
		- Délègue à settings.send_event_reminders()
		- Les erreurs sont loggées mais ne bloquent pas le scheduler
		- Recommandé: appel toutes les heures ou plus fréquent
	"""
	try:
		settings = frappe.get_single('SMS Event Reminder')
		if settings.enabled:
			settings.send_event_reminders()
	except Exception as e:
		frappe.log_error(f"Erreur traitement rappels événements: {e}")

@frappe.whitelist()
def get_reminder_statistics() -> dict[str, Any] | None:
	"""API endpoint pour récupérer les statistiques des rappels.

	Fonction whitelistée pour obtenir les statistiques d'envoi
	de rappels depuis l'interface.

	Returns:
		dict[str, Any] | None: Statistiques avec:
			- enabled (bool): État de l'intégration
			- total_sent (int): Total rappels envoyés
			- sent_today (int): Rappels envoyés aujourd'hui
			- failed_count (int): Nombre d'échecs
			- last_sent (datetime): Dernier envoi réussi
			- last_check (datetime): Dernière vérification
			- next_check (datetime): Prochaine vérification planifiée
			Retourne None en cas d'erreur.

	Example:
		>>> # Depuis JavaScript
		>>> frappe.call({
		...     method: "ovh_sms_integration...get_reminder_statistics",
		...     callback: function(r) {
		...         console.log("Total envoyés:", r.message.total_sent);
		...     }
		... })

	Note:
		- Les erreurs sont loggées et retournent None
		- Les compteurs peuvent être 0 si jamais exécuté
	"""
	try:
		settings = frappe.get_single('SMS Event Reminder')
		
		return {
			"enabled": settings.enabled,
			"total_sent": settings.total_reminders_sent or 0,
			"sent_today": settings.reminders_sent_today or 0,
			"failed_count": settings.failed_reminders_count or 0,
			"last_sent": settings.last_reminder_sent,
			"last_check": settings.last_check_time,
			"next_check": settings.next_check_time
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur récupération statistiques: {e}")
		return None
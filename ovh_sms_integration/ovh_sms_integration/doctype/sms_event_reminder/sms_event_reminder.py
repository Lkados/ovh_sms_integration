# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
import requests
import hashlib
import datetime
import re
from frappe.model.document import Document
from frappe import _
from datetime import datetime, timedelta
from jinja2 import Template

class SMSEventReminder(Document):
	def validate(self):
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

	def get_reminder_times(self):
		"""Retourne la liste des heures de rappel"""
		if self.enable_multiple_reminders and self.reminder_times:
			try:
				return [float(x.strip()) for x in self.reminder_times.split(',')]
			except ValueError:
				frappe.log_error("Format invalide pour reminder_times")
				return [float(self.reminder_hours_before)]
		else:
			return [float(self.reminder_hours_before)]

	def get_message_template(self, recipient_type="customer"):
		"""Retourne le template de message approprié"""
		if recipient_type == "customer" and self.customer_template:
			return self.customer_template
		elif recipient_type == "employee" and self.employee_template:
			return self.employee_template
		elif self.default_template:
			return self.default_template
		else:
			return self.reminder_message_template

	def should_send_now(self):
		"""Vérifie si on peut envoyer des SMS maintenant selon les conditions"""
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

	def parse_event_data(self, description):
		"""Parse toutes les données structurées de l'événement"""
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

	def format_message(self, template, event_doc, customer_name=None, employee_name=None):
		"""Formate le message avec les données de l'événement - VERSION MISE À JOUR"""
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

	def extract_event_type_from_description(self, description):
		"""Extrait le type d'événement depuis la description structurée"""
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

	def get_events_for_reminder(self):
		"""Récupère les événements nécessitant un rappel - VERSION MISE À JOUR"""
		if not self.enabled:
			return []
		
		try:
			# Calcul des plages de temps pour les rappels
			reminder_times = self.get_reminder_times()
			now = datetime.now()
			
			conditions = []
			for hours_before in reminder_times:
				start_time = now + timedelta(hours=hours_before-0.5)  # Marge de 30min
				end_time = now + timedelta(hours=hours_before+0.5)
				conditions.append(f"(starts_on BETWEEN '{start_time}' AND '{end_time}')")
			
			time_condition = " OR ".join(conditions)
			
			# Récupération de TOUS les événements dans la plage horaire
			query = f"""
				SELECT name, subject, description, starts_on, ends_on, 
					   event_participants, location
				FROM `tabEvent`
				WHERE ({time_condition})
				AND docstatus = 1
			"""
			
			if self.skip_past_events:
				query += f" AND starts_on > '{now}'"
			
			if self.skip_all_day_events:
				query += " AND all_day = 0"
			
			# Exécution de la requête pour récupérer tous les événements
			all_events = frappe.db.sql(query, as_dict=True)
			
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

	def get_event_contacts(self, event):
		"""Récupère les contacts (clients et employés) d'un événement"""
		contacts = {
			'customers': [],
			'employees': []
		}
		
		try:
			# Récupération des participants
			participants = frappe.db.sql("""
				SELECT reference_doctype, reference_docname
				FROM `tabEvent Participants`
				WHERE parent = %s
			""", event.name, as_dict=True)
			
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

	def get_customer_mobile(self, customer):
		"""Récupère le numéro mobile d'un client"""
		# Vérifier d'abord sur le document Customer
		if hasattr(customer, 'mobile_no') and customer.mobile_no:
			return customer.mobile_no
		
		# Chercher dans les contacts liés
		try:
			contacts = frappe.db.sql("""
				SELECT mobile_no, phone
				FROM `tabContact`
				WHERE name IN (
					SELECT parent FROM `tabDynamic Link`
					WHERE link_doctype = 'Customer' AND link_name = %s
				)
				AND (mobile_no IS NOT NULL OR phone IS NOT NULL)
				LIMIT 1
			""", customer.name, as_dict=True)
			
			if contacts:
				return contacts[0].mobile_no or contacts[0].phone
		except Exception as e:
			frappe.log_error(f"Erreur récupération mobile client {customer.name}: {e}")
		
		return None

	def get_employee_mobile(self, employee):
		"""Récupère le numéro mobile d'un employé"""
		mobile_fields = ['cell_number', 'personal_phone', 'phone']
		
		for field in mobile_fields:
			if hasattr(employee, field) and employee.get(field):
				return employee.get(field)
		
		return None

	def send_event_reminders(self):
		"""Envoie les rappels pour tous les événements éligibles"""
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

	def get_best_sender(self):
		"""Retourne le meilleur expéditeur disponible depuis OVH SMS Settings"""
		try:
			sms_settings = frappe.get_single('OVH SMS Settings')
			if not sms_settings.enabled:
				return "ERPNext"  # Fallback
			
			return sms_settings.get_best_sender()
		except Exception as e:
			frappe.log_error(f"Erreur récupération expéditeur: {e}")
			return "ERPNext"  # Fallback

	def send_sms_reminder(self, message, mobile):
		"""Envoie un SMS de rappel via l'intégration OVH"""
		try:
			sms_settings = frappe.get_single('OVH SMS Settings')
			if not sms_settings.enabled:
				return {"success": False, "message": "OVH SMS non activé"}
			
			return sms_settings.send_sms(message, mobile)
		except Exception as e:
			frappe.log_error(f"Erreur envoi SMS rappel: {e}")
			return {"success": False, "message": str(e)}

	def is_reminder_already_sent(self, event_name):
		"""Vérifie si un rappel a déjà été envoyé pour cet événement"""
		# Vérification dans les logs (optionnel - peut être implémenté selon les besoins)
		return False

	def log_reminder_sent(self, event_name, recipient_name, recipient_type):
		"""Log l'envoi d'un rappel"""
		try:
			# Créer un log d'envoi si nécessaire
			frappe.logger().info(f"Rappel envoyé - Événement: {event_name}, Destinataire: {recipient_name} ({recipient_type})")
		except Exception as e:
			frappe.log_error(f"Erreur logging rappel: {e}")

	def update_statistics(self, sent_count, failed_count):
		"""Met à jour les statistiques d'envoi"""
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
def send_test_reminder():
	"""Envoie un rappel de test"""
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

def process_event_reminders():
	"""Fonction appelée par le scheduler pour traiter les rappels"""
	try:
		settings = frappe.get_single('SMS Event Reminder')
		if settings.enabled:
			settings.send_event_reminders()
	except Exception as e:
		frappe.log_error(f"Erreur traitement rappels événements: {e}")

@frappe.whitelist()
def get_reminder_statistics():
	"""Récupère les statistiques des rappels"""
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
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
import json
import re
from datetime import datetime, timedelta

def get_ovh_sms_settings():
	"""Récupère les paramètres OVH SMS"""
	settings = frappe.get_single('OVH SMS Settings')
	if not settings.enabled:
		return None
	return settings

def send_sms(message, receiver, sender=None, context=None):
	"""Fonction principale d'envoi SMS"""
	settings = get_ovh_sms_settings()
	if not settings:
		frappe.log_error("OVH SMS non configuré")
		return None
	
	try:
		# Formatage du message avec le contexte
		if context:
			message = format_message_template(message, context)
		
		# Validation du numéro
		receiver = validate_phone_number(receiver)
		
		# Envoi du SMS
		result = settings.send_sms(message, receiver, sender)
		return result
		
	except Exception as e:
		frappe.log_error(f"Erreur envoi SMS: {str(e)}")
		return None

def format_message_template(template, context):
	"""Formate un template de message avec les données du contexte"""
	if not template or not context:
		return template
	
	try:
		# Utilise le système de templates Jinja2 de Frappe
		from jinja2 import Template
		
		# Sécurisation des données
		safe_context = {}
		for key, value in context.items():
			if isinstance(value, (str, int, float)):
				safe_context[key] = value
			elif hasattr(value, 'strftime'):  # datetime
				safe_context[key] = value.strftime('%d/%m/%Y %H:%M')
			else:
				safe_context[key] = str(value)
		
		template_obj = Template(template)
		return template_obj.render(**safe_context)
		
	except Exception as e:
		frappe.log_error(f"Erreur formatage template: {str(e)}")
		return template

def validate_phone_number(phone):
	"""Valide et formate un numéro de téléphone"""
	if not phone:
		return None
	
	# Nettoyage du numéro
	phone = re.sub(r'[^\d+]', '', str(phone))
	
	# Format français
	if phone.startswith('0'):
		phone = '+33' + phone[1:]
	elif not phone.startswith('+'):
		phone = '+33' + phone
	
	# Validation basique
	if not re.match(r'^\+\d{10,15}$', phone):
		raise ValueError(f"Numéro de téléphone invalide: {phone}")
	
	return phone

def get_contact_mobile(doc):
	"""Récupère le numéro de mobile d'un document"""
	mobile_fields = ['mobile_no', 'phone_no', 'contact_mobile', 'mobile', 'phone']
	
	for field in mobile_fields:
		if hasattr(doc, field) and doc.get(field):
			return doc.get(field)
	
	# Recherche dans les contacts liés
	if hasattr(doc, 'contact_person') and doc.contact_person:
		contact = frappe.get_doc('Contact', doc.contact_person)
		for field in mobile_fields:
			if hasattr(contact, field) and contact.get(field):
				return contact.get(field)
	
	return None

# Handlers pour les événements de documents
def on_document_update(doc, method):
	"""Handler générique pour les mises à jour de documents"""
	pass

def on_document_submit(doc, method):
	"""Handler générique pour les soumissions de documents"""
	pass

def on_document_cancel(doc, method):
	"""Handler générique pour les annulations de documents"""
	pass

def send_sales_order_sms(doc, method):
	"""Envoie un SMS lors de la soumission d'une commande"""
	settings = get_ovh_sms_settings()
	if not settings or not settings.enable_sales_order_sms:
		return
	
	mobile = get_contact_mobile(doc)
	if not mobile:
		return
	
	template = settings.sales_order_template
	context = {
		'name': doc.name,
		'customer': doc.customer,
		'grand_total': doc.grand_total,
		'currency': doc.currency,
		'transaction_date': doc.transaction_date
	}
	
	send_sms(template, mobile, context=context)

def send_payment_confirmation_sms(doc, method):
	"""Envoie un SMS lors de la confirmation d'un paiement"""
	settings = get_ovh_sms_settings()
	if not settings or not settings.enable_payment_sms:
		return
	
	mobile = get_contact_mobile(doc)
	if not mobile:
		return
	
	template = settings.payment_template
	context = {
		'name': doc.name,
		'paid_amount': doc.paid_amount,
		'currency': doc.paid_from_account_currency,
		'posting_date': doc.posting_date
	}
	
	send_sms(template, mobile, context=context)

def send_delivery_sms(doc, method):
	"""Envoie un SMS lors de l'expédition"""
	settings = get_ovh_sms_settings()
	if not settings or not settings.enable_delivery_sms:
		return
	
	mobile = get_contact_mobile(doc)
	if not mobile:
		return
	
	template = settings.delivery_template
	context = {
		'name': doc.name,
		'customer': doc.customer,
		'posting_date': doc.posting_date
	}
	
	send_sms(template, mobile, context=context)

def send_purchase_order_sms(doc, method):
	"""Envoie un SMS lors de la soumission d'une commande fournisseur"""
	settings = get_ovh_sms_settings()
	if not settings or not settings.enable_purchase_order_sms:
		return
	
	mobile = get_contact_mobile(doc)
	if not mobile:
		return
	
	template = settings.purchase_order_template
	context = {
		'name': doc.name,
		'supplier': doc.supplier,
		'supplier_name': doc.supplier_name,
		'grand_total': doc.grand_total,
		'currency': doc.currency,
		'transaction_date': doc.transaction_date
	}
	
	send_sms(template, mobile, context=context)

# === NOUVELLES FONCTIONS POUR LES RAPPELS D'ÉVÉNEMENTS ===

def send_event_reminder_sms(event_doc, recipient_mobile, recipient_name, recipient_type="customer"):
	"""Envoie un rappel SMS pour un événement spécifique"""
	try:
		reminder_settings = frappe.get_single('SMS Event Reminder')
		
		if not reminder_settings.enabled:
			return {"success": False, "message": "Rappels désactivés"}
		
		# Récupération du template approprié
		template = reminder_settings.get_message_template(recipient_type)
		
		# Formatage du message
		message = format_event_reminder_message(template, event_doc, recipient_name, recipient_type)
		
		# Envoi du SMS
		result = send_sms(message, recipient_mobile)
		
		if result and result.get('success'):
			log_event_reminder_sent(event_doc.name, recipient_name, recipient_type, recipient_mobile)
		
		return result
		
	except Exception as e:
		frappe.log_error(f"Erreur envoi rappel événement {event_doc.name}: {e}")
		return {"success": False, "message": str(e)}

def format_event_reminder_message(template, event_doc, recipient_name=None, recipient_type="customer"):
	"""Formate le message de rappel d'événement"""
	try:
		context = {
			'subject': event_doc.subject or '',
			'description': event_doc.description or '',
			'event_name': event_doc.name,
			'start_date': event_doc.starts_on.strftime('%d/%m/%Y') if event_doc.starts_on else '',
			'start_time': event_doc.starts_on.strftime('%H:%M') if event_doc.starts_on else '',
			'location': getattr(event_doc, 'location', '') or '',
			'customer_name': recipient_name if recipient_type == "customer" else '',
			'employee_name': recipient_name if recipient_type == "employee" else ''
		}
		
		# Calcul de la durée
		if event_doc.starts_on and event_doc.ends_on:
			duration = (event_doc.ends_on - event_doc.starts_on).total_seconds() / 60
			context['duration'] = int(duration)
		else:
			context['duration'] = ''
		
		return format_message_template(template, context)
		
	except Exception as e:
		frappe.log_error(f"Erreur formatage message rappel: {e}")
		return template

def get_events_requiring_reminders():
	"""Récupère les événements nécessitant un rappel"""
	try:
		reminder_settings = frappe.get_single('SMS Event Reminder')
		
		if not reminder_settings.enabled:
			return []
		
		# Calcul des heures de rappel
		reminder_times = reminder_settings.get_reminder_times()
		now = datetime.now()
		
		conditions = []
		for hours_before in reminder_times:
			start_time = now + timedelta(hours=hours_before-0.5)  # Marge de 30min
			end_time = now + timedelta(hours=hours_before+0.5)
			conditions.append(f"(starts_on BETWEEN '{start_time}' AND '{end_time}')")
		
		time_condition = " OR ".join(conditions)
		
		# Requête des événements
		events = frappe.db.sql(f"""
			SELECT name, subject, description, starts_on, ends_on, 
				   event_participants, location
			FROM `tabEvent`
			WHERE ({time_condition})
			AND docstatus = 1
			AND subject LIKE %s
			AND starts_on > %s
		""", (f"%{reminder_settings.event_type_filter}%", now), as_dict=True)
		
		return events
		
	except Exception as e:
		frappe.log_error(f"Erreur récupération événements rappels: {e}")
		return []

def get_event_participants_with_mobile(event_name):
	"""Récupère les participants d'un événement avec leurs numéros mobiles"""
	try:
		participants = []
		
		# Récupération des participants
		event_participants = frappe.db.sql("""
			SELECT reference_doctype, reference_docname
			FROM `tabEvent Participants`
			WHERE parent = %s
		""", event_name, as_dict=True)
		
		for participant in event_participants:
			mobile = None
			name = None
			
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
				participants.append({
					'name': name,
					'mobile': mobile,
					'type': participant_type,
					'doctype': participant.reference_doctype,
					'docname': participant.reference_docname
				})
		
		return participants
		
	except Exception as e:
		frappe.log_error(f"Erreur récupération participants événement {event_name}: {e}")
		return []

def get_customer_mobile_number(customer):
	"""Récupère le numéro mobile d'un client"""
	# Vérifier le champ mobile du customer
	if hasattr(customer, 'mobile_no') and customer.mobile_no:
		return customer.mobile_no
	
	# Chercher dans les contacts
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

def get_employee_mobile_number(employee):
	"""Récupère le numéro mobile d'un employé"""
	mobile_fields = ['cell_number', 'personal_phone', 'phone']
	
	for field in mobile_fields:
		if hasattr(employee, field) and employee.get(field):
			return employee.get(field)
	
	return None

def log_event_reminder_sent(event_name, recipient_name, recipient_type, mobile):
	"""Log l'envoi d'un rappel d'événement"""
	try:
		frappe.logger().info(
			f"Rappel événement envoyé - Événement: {event_name}, "
			f"Destinataire: {recipient_name} ({recipient_type}), Mobile: {mobile}"
		)
		
		# Optionnel: Créer un log structuré dans une table dédiée
		# create_reminder_log_entry(event_name, recipient_name, recipient_type, mobile)
		
	except Exception as e:
		frappe.log_error(f"Erreur logging rappel événement: {e}")

def process_pending_event_reminders():
	"""Traite tous les rappels d'événements en attente"""
	try:
		reminder_settings = frappe.get_single('SMS Event Reminder')
		
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
				event_doc = frappe.get_doc("Event", event_data.name)
				participants = get_event_participants_with_mobile(event_data.name)
				
				for participant in participants:
					# Vérifier si on doit envoyer selon la configuration
					should_send = False
					
					if participant['type'] == 'customer' and reminder_settings.send_to_customer_only:
						should_send = True
					elif participant['type'] == 'employee' and reminder_settings.send_to_employee:
						should_send = True
					elif not reminder_settings.send_to_customer_only and not reminder_settings.send_to_employee:
						should_send = True  # Envoyer à tous par défaut
					
					if should_send:
						result = send_event_reminder_sms(
							event_doc, 
							participant['mobile'], 
							participant['name'],
							participant['type']
						)
						
						if result and result.get('success'):
							total_sent += 1
						else:
							total_failed += 1
			
			except Exception as e:
				frappe.log_error(f"Erreur traitement événement {event_data.name}: {e}")
				total_failed += 1
		
		# Mise à jour des statistiques
		if total_sent > 0 or total_failed > 0:
			update_reminder_statistics(total_sent, total_failed)
		
		return {
			"success": True,
			"message": f"Traitement terminé: {total_sent} envoyés, {total_failed} échoués",
			"sent": total_sent,
			"failed": total_failed
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur traitement rappels événements: {e}")
		return {"success": False, "message": str(e)}

def update_reminder_statistics(sent_count, failed_count):
	"""Met à jour les statistiques des rappels"""
	try:
		reminder_settings = frappe.get_single('SMS Event Reminder')
		now = datetime.now()
		
		# Mise à jour des compteurs
		reminder_settings.db_set('total_reminders_sent', 
			(reminder_settings.total_reminders_sent or 0) + sent_count)
		reminder_settings.db_set('failed_reminders_count', 
			(reminder_settings.failed_reminders_count or 0) + failed_count)
		reminder_settings.db_set('last_check_time', now)
		
		if sent_count > 0:
			reminder_settings.db_set('last_reminder_sent', now)
		
		# Compteur journalier
		today = now.date()
		last_check = reminder_settings.last_check_time.date() if reminder_settings.last_check_time else None
		
		if last_check != today:
			reminder_settings.db_set('reminders_sent_today', sent_count)
		else:
			reminder_settings.db_set('reminders_sent_today', 
				(reminder_settings.reminders_sent_today or 0) + sent_count)
		
		frappe.db.commit()
		
	except Exception as e:
		frappe.log_error(f"Erreur mise à jour statistiques rappels: {e}")

# === FONCTIONS D'API POUR L'INTERFACE ===

@frappe.whitelist()
def get_pending_events():
	"""API pour récupérer les événements en attente de rappel"""
	try:
		events = get_events_requiring_reminders()
		return {
			"success": True,
			"events": events,
			"count": len(events)
		}
	except Exception as e:
		frappe.log_error(f"Erreur API pending events: {e}")
		return {"success": False, "message": str(e)}

@frappe.whitelist()
def manual_send_event_reminder(event_name, test_mode=False):
	"""Envoie manuellement un rappel pour un événement spécifique"""
	try:
		event_doc = frappe.get_doc("Event", event_name)
		participants = get_event_participants_with_mobile(event_name)
		
		if not participants:
			return {"success": False, "message": "Aucun participant avec mobile trouvé"}
		
		results = []
		for participant in participants:
			if not test_mode:
				result = send_event_reminder_sms(
					event_doc, 
					participant['mobile'], 
					participant['name'],
					participant['type']
				)
			else:
				result = {"success": True, "message": "Mode test - SMS non envoyé"}
			
			results.append({
				"participant": participant['name'],
				"type": participant['type'],
				"mobile": participant['mobile'],
				"result": result
			})
		
		success_count = sum(1 for r in results if r['result'].get('success'))
		
		return {
			"success": success_count > 0,
			"message": f"{success_count}/{len(results)} rappels envoyés",
			"details": results
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur envoi rappel manuel: {e}")
		return {"success": False, "message": str(e)}

# === ANCIENNES FONCTIONS CONSERVÉES ===

def send_daily_reminders():
	"""Envoie les rappels quotidiens"""
	# Implémentation des rappels quotidiens
	pass

def send_weekly_reports():
	"""Envoie les rapports hebdomadaires"""
	# Implémentation des rapports hebdomadaires
	pass

@frappe.whitelist()
def test_ovh_connection():
	"""Test la connexion OVH"""
	settings = get_ovh_sms_settings()
	if not settings:
		return {"success": False, "message": "OVH SMS non configuré"}
	
	return settings.test_connection()

@frappe.whitelist()
def send_manual_sms(message, receivers, sender=None):
	"""Envoie un SMS manuel"""
	if isinstance(receivers, str):
		receivers = [receivers]
	
	results = []
	for receiver in receivers:
		result = send_sms(message, receiver, sender)
		results.append({
			"receiver": receiver,
			"success": result is not None,
			"result": result
		})
	
	return results

@frappe.whitelist()
def get_sms_balance():
	"""Récupère le solde SMS"""
	settings = get_ovh_sms_settings()
	if not settings:
		return None
	
	return settings.get_sms_balance()

def format_sms_message(template, doc):
	"""Fonction Jinja pour formater les messages SMS"""
	if not template or not doc:
		return template
	
	context = doc.as_dict()
	return format_message_template(template, context)
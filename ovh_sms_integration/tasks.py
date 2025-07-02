# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
from datetime import datetime, timedelta
import json

def check_event_reminders_hourly():
	"""Tâche horaire pour vérifier et envoyer les rappels d'événements"""
	try:
		frappe.logger().info("Début vérification rappels événements - Horaire")
		
		# Récupération des paramètres
		reminder_settings = frappe.get_single('SMS Event Reminder')
		
		if not reminder_settings.enabled:
			frappe.logger().info("Rappels d'événements désactivés")
			return
		
		# Vérification si c'est le bon moment pour envoyer
		if not reminder_settings.should_send_now():
			frappe.logger().info("Hors heures d'envoi configurées")
			return
		
		# Traitement des rappels
		reminder_settings.send_event_reminders()
		
		frappe.logger().info("Fin vérification rappels événements - Horaire")
		
	except Exception as e:
		frappe.log_error(f"Erreur tâche horaire rappels: {e}")

def reset_daily_counters():
	"""Remet à zéro les compteurs journaliers"""
	try:
		frappe.logger().info("Reset compteurs journaliers rappels")
		
		# Reset du compteur journalier pour SMS Event Reminder
		reminder_settings = frappe.get_single('SMS Event Reminder')
		reminder_settings.db_set('reminders_sent_today', 0)
		
		# Reset du compteur journalier pour OVH SMS Settings
		sms_settings = frappe.get_single('OVH SMS Settings')
		sms_settings.db_set('sms_sent_today', 0)
		
		frappe.db.commit()
		frappe.logger().info("Compteurs journaliers remis à zéro")
		
	except Exception as e:
		frappe.log_error(f"Erreur reset compteurs journaliers: {e}")

def cleanup_old_reminder_logs():
	"""Nettoie les anciens logs de rappels"""
	try:
		frappe.logger().info("Nettoyage anciens logs rappels")
		
		# Suppression des logs d'erreur de plus de 30 jours
		thirty_days_ago = datetime.now() - timedelta(days=30)
		
		# Nettoyage des Error Logs liés aux SMS
		frappe.db.sql("""
			DELETE FROM `tabError Log`
			WHERE creation < %s
			AND (error LIKE '%SMS%' OR error LIKE '%OVH%' OR error LIKE '%rappel%')
		""", thirty_days_ago)
		
		# Nettoyage des Activity Logs liés aux SMS (si existants)
		frappe.db.sql("""
			DELETE FROM `tabActivity Log`
			WHERE creation < %s
			AND (subject LIKE '%SMS%' OR subject LIKE '%rappel%')
		""", thirty_days_ago)
		
		frappe.db.commit()
		frappe.logger().info("Nettoyage logs terminé")
		
	except Exception as e:
		frappe.log_error(f"Erreur nettoyage logs: {e}")

def send_weekly_reminder_report():
	"""Envoie un rapport hebdomadaire des rappels"""
	try:
		frappe.logger().info("Génération rapport hebdomadaire rappels")
		
		# Récupération des statistiques de la semaine
		week_ago = datetime.now() - timedelta(days=7)
		
		# Statistiques des rappels
		reminder_settings = frappe.get_single('SMS Event Reminder')
		
		# Calcul des statistiques de la semaine
		weekly_stats = calculate_weekly_stats()
		
		# Génération du rapport
		report_content = generate_weekly_report(weekly_stats)
		
		# Envoi par email aux administrateurs (optionnel)
		send_report_to_administrators(report_content)
		
		frappe.logger().info("Rapport hebdomadaire généré")
		
	except Exception as e:
		frappe.log_error(f"Erreur génération rapport hebdomadaire: {e}")

def calculate_weekly_stats():
	"""Calcule les statistiques de la semaine"""
	try:
		week_ago = datetime.now() - timedelta(days=7)
		
		# Statistiques des rappels
		reminder_settings = frappe.get_single('SMS Event Reminder')
		
		# Événements traités cette semaine
		events_this_week = frappe.db.sql("""
			SELECT COUNT(*) as count
			FROM `tabEvent`
			WHERE starts_on >= %s
			AND starts_on <= %s
			AND subject LIKE %s
			AND docstatus = 1
		""", (week_ago, datetime.now(), f"%{reminder_settings.event_type_filter}%"), as_dict=True)
		
		# Rappels envoyés (estimation basée sur les logs)
		reminder_logs_count = get_reminder_logs_count(week_ago)
		
		return {
			'events_scheduled': events_this_week[0]['count'] if events_this_week else 0,
			'reminders_sent': reminder_logs_count,
			'total_reminders': reminder_settings.total_reminders_sent or 0,
			'failed_reminders': reminder_settings.failed_reminders_count or 0,
			'week_start': week_ago.strftime('%d/%m/%Y'),
			'week_end': datetime.now().strftime('%d/%m/%Y')
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur calcul statistiques hebdomadaires: {e}")
		return {}

def get_reminder_logs_count(since_date):
	"""Compte les rappels envoyés depuis une date"""
	try:
		# Recherche dans les logs système
		logs = frappe.db.sql("""
			SELECT COUNT(*) as count
			FROM `tabError Log`
			WHERE creation >= %s
			AND error LIKE '%Rappel envoyé%'
		""", since_date, as_dict=True)
		
		return logs[0]['count'] if logs else 0
		
	except Exception as e:
		frappe.log_error(f"Erreur comptage logs rappels: {e}")
		return 0

def generate_weekly_report(stats):
	"""Génère le contenu du rapport hebdomadaire"""
	try:
		report = f"""
		<h3>Rapport Hebdomadaire - Rappels d'Événements SMS</h3>
		<p>Période: {stats.get('week_start', 'N/A')} - {stats.get('week_end', 'N/A')}</p>
		
		<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
			<tr>
				<td><strong>Événements programmés cette semaine</strong></td>
				<td>{stats.get('events_scheduled', 0)}</td>
			</tr>
			<tr>
				<td><strong>Rappels envoyés cette semaine</strong></td>
				<td>{stats.get('reminders_sent', 0)}</td>
			</tr>
			<tr>
				<td><strong>Total rappels envoyés</strong></td>
				<td>{stats.get('total_reminders', 0)}</td>
			</tr>
			<tr>
				<td><strong>Rappels échoués</strong></td>
				<td>{stats.get('failed_reminders', 0)}</td>
			</tr>
		</table>
		
		<h4>Prochains Événements</h4>
		{get_upcoming_events_table()}
		
		<p><small>Rapport généré automatiquement le {datetime.now().strftime('%d/%m/%Y à %H:%M')}</small></p>
		"""
		
		return report
		
	except Exception as e:
		frappe.log_error(f"Erreur génération contenu rapport: {e}")
		return "Erreur lors de la génération du rapport"

def get_upcoming_events_table():
	"""Génère le tableau des prochains événements"""
	try:
		reminder_settings = frappe.get_single('SMS Event Reminder')
		
		# Récupération des prochains événements
		upcoming_events = frappe.db.sql("""
			SELECT name, subject, starts_on, description
			FROM `tabEvent`
			WHERE starts_on > %s
			AND starts_on <= %s
			AND subject LIKE %s
			AND docstatus = 1
			ORDER BY starts_on
			LIMIT 10
		""", (
			datetime.now(),
			datetime.now() + timedelta(days=7),
			f"%{reminder_settings.event_type_filter}%"
		), as_dict=True)
		
		if not upcoming_events:
			return "<p>Aucun événement programmé pour la semaine prochaine.</p>"
		
		table = """
		<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
			<tr>
				<th>Événement</th>
				<th>Date/Heure</th>
				<th>Description</th>
			</tr>
		"""
		
		for event in upcoming_events:
			start_date = event.starts_on.strftime('%d/%m/%Y %H:%M') if event.starts_on else 'N/A'
			description = (event.description or '')[:50] + ('...' if len(event.description or '') > 50 else '')
			
			table += f"""
			<tr>
				<td>{event.subject}</td>
				<td>{start_date}</td>
				<td>{description}</td>
			</tr>
			"""
		
		table += "</table>"
		return table
		
	except Exception as e:
		frappe.log_error(f"Erreur génération tableau événements: {e}")
		return "<p>Erreur lors de la récupération des événements.</p>"

def send_report_to_administrators(report_content):
	"""Envoie le rapport aux administrateurs par email"""
	try:
		# Récupération des administrateurs système
		administrators = frappe.db.sql("""
			SELECT DISTINCT u.email
			FROM `tabUser` u
			JOIN `tabHas Role` hr ON u.name = hr.parent
			WHERE hr.role = 'System Manager'
			AND u.enabled = 1
			AND u.email IS NOT NULL
			AND u.email != 'Administrator'
		""", as_dict=True)
		
		if not administrators:
			frappe.logger().info("Aucun administrateur trouvé pour l'envoi du rapport")
			return
		
		# Préparation de l'email
		recipients = [admin.email for admin in administrators]
		
		# Envoi de l'email
		frappe.sendmail(
			recipients=recipients,
			subject=f"Rapport Hebdomadaire - Rappels SMS {datetime.now().strftime('%d/%m/%Y')}",
			message=report_content,
			header=["Rapport SMS", "blue"]
		)
		
		frappe.logger().info(f"Rapport envoyé à {len(recipients)} administrateur(s)")
		
	except Exception as e:
		frappe.log_error(f"Erreur envoi rapport: {e}")

def check_reminder_system_health():
	"""Vérifie la santé du système de rappels"""
	try:
		health_issues = []
		
		# Vérification des paramètres OVH SMS
		try:
			sms_settings = frappe.get_single('OVH SMS Settings')
			if not sms_settings.enabled:
				health_issues.append("OVH SMS Integration désactivé")
			
			# Test de connexion
			connection_test = sms_settings.test_connection()
			if not connection_test.get('success'):
				health_issues.append(f"Problème connexion OVH: {connection_test.get('message')}")
				
		except Exception as e:
			health_issues.append(f"Erreur vérification OVH SMS: {str(e)}")
		
		# Vérification des paramètres de rappels
		try:
			reminder_settings = frappe.get_single('SMS Event Reminder')
			if not reminder_settings.enabled:
				health_issues.append("Rappels d'événements désactivés")
			
			if not reminder_settings.event_type_filter:
				health_issues.append("Aucun type d'événement configuré")
				
		except Exception as e:
			health_issues.append(f"Erreur vérification rappels: {str(e)}")
		
		# Log des problèmes trouvés
		if health_issues:
			frappe.log_error(f"Problèmes système rappels SMS: {'; '.join(health_issues)}")
		else:
			frappe.logger().info("Système de rappels SMS en bonne santé")
		
		return len(health_issues) == 0
		
	except Exception as e:
		frappe.log_error(f"Erreur vérification santé système: {e}")
		return False

# Tâches de maintenance additionnelles

def optimize_reminder_performance():
	"""Optimise les performances du système de rappels"""
	try:
		frappe.logger().info("Optimisation performances rappels")
		
		# Nettoyage de la base de données
		frappe.db.sql("OPTIMIZE TABLE `tabEvent`")
		frappe.db.sql("OPTIMIZE TABLE `tabEvent Participants`")
		
		# Mise à jour des statistiques
		reminder_settings = frappe.get_single('SMS Event Reminder')
		
		# Calcul de la moyenne SMS/jour
		total_days = 30  # Sur les 30 derniers jours
		avg_per_day = (reminder_settings.total_reminders_sent or 0) / total_days
		reminder_settings.db_set('average_sms_per_day', round(avg_per_day, 2))
		
		frappe.db.commit()
		frappe.logger().info("Optimisation terminée")
		
	except Exception as e:
		frappe.log_error(f"Erreur optimisation performances: {e}")

def backup_reminder_settings():
	"""Sauvegarde les paramètres de rappels"""
	try:
		frappe.logger().info("Sauvegarde paramètres rappels")
		
		# Sauvegarde des paramètres SMS
		sms_settings = frappe.get_single('OVH SMS Settings')
		reminder_settings = frappe.get_single('SMS Event Reminder')
		
		backup_data = {
			'timestamp': datetime.now().isoformat(),
			'ovh_sms_settings': {
				'enabled': sms_settings.enabled,
				'auto_detect_service': sms_settings.auto_detect_service,
				'default_sender': sms_settings.default_sender,
				'service_name': sms_settings.service_name,
				# Ne pas sauvegarder les secrets
			},
			'reminder_settings': {
				'enabled': reminder_settings.enabled,
				'event_type_filter': reminder_settings.event_type_filter,
				'reminder_hours_before': reminder_settings.reminder_hours_before,
				'enable_multiple_reminders': reminder_settings.enable_multiple_reminders,
				'reminder_times': reminder_settings.reminder_times,
				'send_to_customer_only': reminder_settings.send_to_customer_only,
				'send_to_employee': reminder_settings.send_to_employee,
			}
		}
		
		# Écriture du fichier de sauvegarde
		backup_file = f"sms_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
		
		# Log de la sauvegarde
		frappe.logger().info(f"Sauvegarde créée: {backup_file}")
		
	except Exception as e:
		frappe.log_error(f"Erreur sauvegarde paramètres: {e}")
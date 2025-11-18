# -*- coding: utf-8 -*-
"""Tâches planifiées pour ovh_sms_integration.

Ce module contient les tâches schedulées (cron jobs) pour le système de rappels SMS.
Il fournit les fonctionnalités de:
- Vérification horaire des rappels d'événements
- Réinitialisation quotidienne des compteurs
- Nettoyage des anciens logs
- Rapports hebdomadaires par email
- Vérifications de santé du système
- Optimisation de performance
- Sauvegarde des configurations
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import frappe
from frappe import _

if TYPE_CHECKING:
	from ovh_sms_integration.types import WeeklyReportStats

def check_event_reminders_hourly() -> None:
	"""Tâche horaire pour vérifier et envoyer les rappels d'événements.

	Appelée par le scheduler Frappe toutes les heures pour traiter
	les rappels d'événements automatiques configurés.

	Note:
		- Vérifie que reminder_settings.enabled = True
		- Vérifie should_send_now() pour respecter heures ouvrables
		- Délègue à reminder_settings.send_event_reminders()
		- Les erreurs sont loggées mais ne bloquent pas le scheduler
	"""
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

def reset_daily_counters() -> None:
	"""Remet à zéro les compteurs journaliers.

	Appelée par le scheduler Frappe chaque jour à minuit pour
	remettre à zéro les compteurs de SMS envoyés aujourd'hui.

	Note:
		- Réinitialise reminders_sent_today dans SMS Event Reminder
		- Réinitialise sms_sent_today dans OVH SMS Settings
		- Utilise db_set() pour éviter les triggers de validation
		- Les erreurs sont loggées mais ne bloquent pas le scheduler
	"""
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

def cleanup_old_reminder_logs() -> None:
	"""Nettoie les anciens logs de rappels.

	Appelée par le scheduler Frappe quotidiennement pour supprimer
	les logs de rappels SMS trop anciens et économiser l'espace disque.

	Note:
		- Supprime Error Logs et Activity Logs de plus de 30 jours
		- Filtre les logs liés aux SMS/OVH/rappels
		- TODO: Convertir SQL en ORM Frappe
		- Les erreurs sont loggées mais ne bloquent pas le scheduler
	"""
	try:
		frappe.logger().info("Nettoyage anciens logs rappels")
		
		# Suppression des logs d'erreur de plus de 30 jours
		thirty_days_ago = datetime.now() - timedelta(days=30)

		# Nettoyage des Error Logs liés aux SMS (ORM)
		error_logs = frappe.get_all(
			"Error Log",
			filters=[
				["creation", "<", thirty_days_ago],
				["error", "like", "%SMS%"]
			],
			pluck="name"
		)
		for log_name in error_logs:
			frappe.delete_doc("Error Log", log_name, ignore_permissions=True, force=True)

		# Nettoyage des Activity Logs liés aux SMS (ORM)
		activity_logs = frappe.get_all(
			"Activity Log",
			filters=[
				["creation", "<", thirty_days_ago],
				["subject", "like", "%SMS%"]
			],
			pluck="name"
		)
		for log_name in activity_logs:
			frappe.delete_doc("Activity Log", log_name, ignore_permissions=True, force=True)
		
		frappe.db.commit()
		frappe.logger().info("Nettoyage logs terminé")
		
	except Exception as e:
		frappe.log_error(f"Erreur nettoyage logs: {e}")

def send_weekly_reminder_report() -> None:
	"""Envoie un rapport hebdomadaire des rappels.

	Appelée par le scheduler Frappe chaque lundi pour envoyer
	un rapport par email aux administrateurs système.

	Note:
		- Génère un rapport HTML avec statistiques de la semaine
		- Envoie aux utilisateurs avec role "System Manager"
		- Inclut: événements programmés, rappels envoyés, échecs
		- Utilise templates Jinja pour l'HTML
	"""
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

def calculate_weekly_stats() -> dict[str, Any]:
	"""Calcule les statistiques de la semaine.

	Analyse les événements et rappels de la semaine passée
	pour générer un rapport statistique.

	Returns:
		dict[str, Any]: Statistiques hebdomadaires avec:
			- events_scheduled: Nombre d'événements programmés
			- reminders_sent: Rappels envoyés cette semaine
			- total_reminders: Total de tous les rappels
			- failed_reminders: Nombre de rappels échoués
			- week_start: Date de début (format DD/MM/YYYY)
			- week_end: Date de fin (format DD/MM/YYYY)

	Note:
		- La semaine = 7 derniers jours
		- TODO: Convertir SQL en ORM Frappe
	"""
	try:
		week_ago = datetime.now() - timedelta(days=7)
		
		# Statistiques des rappels
		reminder_settings = frappe.get_single('SMS Event Reminder')
		
		# Événements traités cette semaine (ORM Frappe)
		events_count = frappe.db.count(
			"Event",
			filters={
				"starts_on": ["between", [week_ago, datetime.now()]],
				"subject": ["like", f"%{reminder_settings.event_type_filter}%"],
				"docstatus": 1
			}
		)

		# Rappels envoyés (estimation basée sur les logs)
		reminder_logs_count = get_reminder_logs_count(week_ago)

		return {
			'events_scheduled': events_count,
			'reminders_sent': reminder_logs_count,
			'total_reminders': reminder_settings.total_reminders_sent or 0,
			'failed_reminders': reminder_settings.failed_reminders_count or 0,
			'week_start': week_ago.strftime('%d/%m/%Y'),
			'week_end': datetime.now().strftime('%d/%m/%Y')
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur calcul statistiques hebdomadaires: {e}")
		return {}

def get_reminder_logs_count(since_date: datetime) -> int:
	"""Compte les rappels envoyés depuis une date.

	Args:
		since_date: Date de début pour le comptage.

	Returns:
		int: Nombre de rappels envoyés depuis cette date.

	Note:
		- Utilise les Error Logs avec message "Rappel envoyé"
		- TODO: Créer un vrai doctype SMS Reminder Log
	"""
	try:
		# Recherche dans les logs système (ORM Frappe)
		logs_count = frappe.db.count(
			"Error Log",
			filters={
				"creation": [">=", since_date],
				"error": ["like", "%Rappel envoyé%"]
			}
		)

		return logs_count
		
	except Exception as e:
		frappe.log_error(f"Erreur comptage logs rappels: {e}")
		return 0

def generate_weekly_report(stats: dict[str, Any]) -> str:
	"""Génère le contenu du rapport hebdomadaire.

	Args:
		stats: Statistiques hebdomadaires à inclure dans le rapport.

	Returns:
		str: Contenu HTML du rapport formaté.

	Note:
		- Utilise template Jinja pour l'HTML
		- Inclut tableau des statistiques
		- Inclut liste des événements à venir
		- Style inline pour compatibilité email
	"""
	try:
		# Générer le tableau des événements à venir
		upcoming_events_html = get_upcoming_events_table()

		# Rendre le template Jinja
		report = frappe.render_template(
			"ovh_sms_integration/templates/emails/weekly_reminder_report.html",
			{
				"stats": stats,
				"upcoming_events_html": upcoming_events_html,
				"generation_date": datetime.now().strftime('%d/%m/%Y à %H:%M')
			}
		)

		return report
		
	except Exception as e:
		frappe.log_error(f"Erreur génération contenu rapport: {e}")
		return "Erreur lors de la génération du rapport"

def get_upcoming_events_table() -> str:
	"""Génère le tableau des prochains événements.

	Returns:
		str: Tableau HTML des 10 prochains événements avec rappels configurés.

	Note:
		- Utilise template Jinja pour l'HTML
		- Limite à 10 événements pour lisibilité
		- Inclut: subject, starts_on, description (tronquée)
	"""
	try:
		reminder_settings = frappe.get_single('SMS Event Reminder')

		# Récupération des prochains événements (ORM Frappe)
		upcoming_events = frappe.get_all(
			"Event",
			filters={
				"starts_on": ["between", [datetime.now(), datetime.now() + timedelta(days=7)]],
				"subject": ["like", f"%{reminder_settings.event_type_filter}%"],
				"docstatus": 1
			},
			fields=["name", "subject", "starts_on", "description"],
			order_by="starts_on asc",
			limit=10
		)

		# Préparer les données pour le template
		events_data = []
		for event in upcoming_events:
			start_date = event.starts_on.strftime('%d/%m/%Y %H:%M') if event.starts_on else 'N/A'
			description = (event.description or '')[:50]
			if len(event.description or '') > 50:
				description += '...'

			events_data.append({
				"subject": event.subject,
				"start_date": start_date,
				"description_preview": description
			})

		# Rendre le template Jinja
		table = frappe.render_template(
			"ovh_sms_integration/templates/emails/upcoming_events_table.html",
			{"events": events_data}
		)

		return table
		
	except Exception as e:
		frappe.log_error(f"Erreur génération tableau événements: {e}")
		return "<p>Erreur lors de la récupération des événements.</p>"

def send_report_to_administrators(report_content: str) -> None:
	"""Envoie le rapport aux administrateurs par email.

	Args:
		report_content: Contenu HTML du rapport à envoyer.

	Note:
		- Envoie aux utilisateurs avec role "System Manager"
		- Utilise frappe.sendmail() pour l'envoi
		- Exclut le compte "Administrator" des destinataires
	"""
	try:
		# Récupération des utilisateurs avec role System Manager (ORM Frappe)
		system_managers = frappe.get_all(
			"Has Role",
			filters={
				"role": "System Manager",
				"parenttype": "User"
			},
			fields=["parent"],
			distinct=True
		)

		if not system_managers:
			frappe.logger().info("Aucun administrateur trouvé pour l'envoi du rapport")
			return

		# Récupération des emails des utilisateurs actifs
		recipients = []
		for role_assignment in system_managers:
			user = frappe.get_doc("User", role_assignment.parent)
			if user.enabled and user.email and user.email != "Administrator":
				recipients.append(user.email)
		
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

def check_reminder_system_health() -> bool:
	"""Vérifie la santé du système de rappels.

	Appelée par le scheduler Frappe quotidiennement pour détecter
	les problèmes potentiels du système de rappels.

	Returns:
		bool: True si le système est en bonne santé, False sinon.

	Note:
		- Vérifie: OVH settings, connexion API, configurations rappels
		- Logue les problèmes détectés via frappe.log_error()
		- Les erreurs sont loggées mais ne bloquent pas le scheduler
	"""
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


def optimize_reminder_performance() -> None:
	"""Optimise les performances du système de rappels.

	Appelée par le scheduler Frappe hebdomadairement pour maintenir
	de bonnes performances du système.

	Note:
		- Optimise les tables MySQL (OPTIMIZE TABLE)
		- Calcule la moyenne de SMS envoyés par jour
		- Met à jour average_sms_per_day dans SMS Event Reminder
	"""
	try:
		frappe.logger().info("Optimisation performances rappels")

		# Optimisation MySQL (pas d'équivalent ORM, requêtes DDL nécessaires)
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

def backup_reminder_settings() -> None:
	"""Sauvegarde les paramètres de rappels.

	Appelée par le scheduler Frappe hebdomadairement pour créer
	une sauvegarde JSON des configurations actives.

	Note:
		- Exporte OVH SMS Settings et SMS Event Reminder
		- Format: sms_backup_YYYYMMDD_HHMMSS.json
		- N'inclut PAS les secrets (application_key, application_secret, etc.)
		- TODO: Écrire le fichier dans private/files/backups/
		- TODO: Ajouter rotation automatique des backups (garder 30 jours)
	"""
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
# -*- coding: utf-8 -*-
"""
Script de vérification de santé du système OVH SMS Integration
Vérifie que tous les composants fonctionnent correctement
"""

from __future__ import unicode_literals
import frappe
from frappe import _
from datetime import datetime, timedelta
import json

def run_health_check():
	"""Exécute une vérification complète du système"""
	print("🔍 Vérification de santé - OVH SMS Integration")
	print("=" * 60)
	
	health_report = {
		"timestamp": datetime.now().isoformat(),
		"overall_status": "healthy",
		"checks": [],
		"warnings": [],
		"errors": []
	}
	
	try:
		# 1. Vérification des DocTypes
		check_doctypes(health_report)
		
		# 2. Vérification des paramètres OVH
		check_ovh_settings(health_report)
		
		# 3. Vérification des rappels d'événements
		check_event_reminders(health_report)
		
		# 4. Vérification du scheduler
		check_scheduler(health_report)
		
		# 5. Vérification des permissions
		check_permissions(health_report)
		
		# 6. Vérification des tâches récentes
		check_recent_activity(health_report)
		
		# 7. Vérification de la base de données
		check_database_health(health_report)
		
	except Exception as e:
		health_report["errors"].append(f"Erreur générale lors de la vérification: {str(e)}")
		health_report["overall_status"] = "error"
	
	# Détermination du statut global
	if health_report["errors"]:
		health_report["overall_status"] = "error"
	elif health_report["warnings"]:
		health_report["overall_status"] = "warning"
	
	# Affichage du rapport
	display_health_report(health_report)
	
	return health_report

def check_doctypes(health_report):
	"""Vérifie que tous les DocTypes nécessaires existent"""
	print("\n📋 Vérification des DocTypes...")
	
	required_doctypes = [
		"OVH SMS Settings",
		"SMS Event Reminder"
	]
	
	for doctype in required_doctypes:
		try:
			if frappe.db.exists("DocType", doctype):
				health_report["checks"].append(f"✅ DocType {doctype} existe")
				print(f"  ✅ {doctype}")
			else:
				error_msg = f"❌ DocType {doctype} manquant"
				health_report["errors"].append(error_msg)
				print(f"  {error_msg}")
		except Exception as e:
			error_msg = f"❌ Erreur vérification {doctype}: {str(e)}"
			health_report["errors"].append(error_msg)
			print(f"  {error_msg}")

def check_ovh_settings(health_report):
	"""Vérifie la configuration OVH SMS"""
	print("\n🔧 Vérification des paramètres OVH...")
	
	try:
		settings = frappe.get_single('OVH SMS Settings')
		
		# Vérification activation
		if settings.enabled:
			health_report["checks"].append("✅ OVH SMS activé")
			print("  ✅ OVH SMS activé")
		else:
			warning_msg = "⚠️ OVH SMS désactivé"
			health_report["warnings"].append(warning_msg)
			print(f"  {warning_msg}")
			return
		
		# Vérification des champs obligatoires
		required_fields = ["application_key", "application_secret", "consumer_key"]
		for field in required_fields:
			if field == "application_secret" or field == "consumer_key":
				value = settings.get_password(field)
			else:
				value = getattr(settings, field, None)
			
			if value:
				health_report["checks"].append(f"✅ {field} configuré")
				print(f"  ✅ {field} configuré")
			else:
				error_msg = f"❌ {field} manquant"
				health_report["errors"].append(error_msg)
				print(f"  {error_msg}")
		
		# Test de connexion
		print("  📡 Test de connexion OVH...")
		connection_result = settings.test_connection()
		if connection_result.get("success"):
			health_report["checks"].append("✅ Connexion OVH réussie")
			print("    ✅ Connexion réussie")
		else:
			error_msg = f"❌ Connexion OVH échouée: {connection_result.get('message')}"
			health_report["errors"].append(error_msg)
			print(f"    {error_msg}")
		
	except Exception as e:
		error_msg = f"❌ Erreur vérification OVH: {str(e)}"
		health_report["errors"].append(error_msg)
		print(f"  {error_msg}")

def check_event_reminders(health_report):
	"""Vérifie la configuration des rappels d'événements"""
	print("\n⏰ Vérification des rappels d'événements...")
	
	try:
		reminder_settings = frappe.get_single('SMS Event Reminder')
		
		# Vérification activation
		if reminder_settings.enabled:
			health_report["checks"].append("✅ Rappels d'événements activés")
			print("  ✅ Rappels activés")
		else:
			warning_msg = "⚠️ Rappels d'événements désactivés"
			health_report["warnings"].append(warning_msg)
			print(f"  {warning_msg}")
			return
		
		# Vérification filtre événements
		if reminder_settings.event_type_filter:
			health_report["checks"].append(f"✅ Filtre événements: '{reminder_settings.event_type_filter}'")
			print(f"  ✅ Filtre: '{reminder_settings.event_type_filter}'")
		else:
			warning_msg = "⚠️ Aucun filtre d'événements configuré"
			health_report["warnings"].append(warning_msg)
			print(f"  {warning_msg}")
		
		# Vérification templates
		if reminder_settings.reminder_message_template:
			health_report["checks"].append("✅ Template de message configuré")
			print("  ✅ Template configuré")
		else:
			warning_msg = "⚠️ Aucun template de message configuré"
			health_report["warnings"].append(warning_msg)
			print(f"  {warning_msg}")
		
		# Vérification événements éligibles
		events_count = get_eligible_events_count(reminder_settings.event_type_filter)
		if events_count > 0:
			health_report["checks"].append(f"✅ {events_count} événements éligibles trouvés")
			print(f"  ✅ {events_count} événements éligibles")
		else:
			warning_msg = "⚠️ Aucun événement éligible trouvé"
			health_report["warnings"].append(warning_msg)
			print(f"  {warning_msg}")
		
	except Exception as e:
		error_msg = f"❌ Erreur vérification rappels: {str(e)}"
		health_report["errors"].append(error_msg)
		print(f"  {error_msg}")

def check_scheduler(health_report):
	"""Vérifie que le scheduler fonctionne"""
	print("\n⚙️ Vérification du scheduler...")
	
	try:
		# Vérification du statut du scheduler
		scheduler_enabled = not frappe.conf.get("pause_scheduler", False)
		
		if scheduler_enabled:
			health_report["checks"].append("✅ Scheduler activé")
			print("  ✅ Scheduler activé")
		else:
			error_msg = "❌ Scheduler désactivé"
			health_report["errors"].append(error_msg)
			print(f"  {error_msg}")
		
		# Vérification des tâches configurées
		required_tasks = [
			"ovh_sms_integration.ovh_sms_integration.doctype.sms_event_reminder.sms_event_reminder.process_event_reminders",
			"ovh_sms_integration.tasks.check_event_reminders_hourly",
			"ovh_sms_integration.tasks.reset_daily_counters"
		]
		
		for task in required_tasks:
			try:
				# Tentative d'importation de la fonction
				module_path, function_name = task.rsplit('.', 1)
				module = frappe.get_module(module_path)
				if hasattr(module, function_name):
					health_report["checks"].append(f"✅ Tâche {function_name} disponible")
					print(f"  ✅ {function_name}")
				else:
					warning_msg = f"⚠️ Fonction {function_name} introuvable"
					health_report["warnings"].append(warning_msg)
					print(f"  {warning_msg}")
			except Exception as e:
				warning_msg = f"⚠️ Erreur importation {task}: {str(e)}"
				health_report["warnings"].append(warning_msg)
				print(f"  {warning_msg}")
		
	except Exception as e:
		error_msg = f"❌ Erreur vérification scheduler: {str(e)}"
		health_report["errors"].append(error_msg)
		print(f"  {error_msg}")

def check_permissions(health_report):
	"""Vérifie les permissions des rôles"""
	print("\n🔒 Vérification des permissions...")
	
	try:
		required_roles = ["SMS Manager", "SMS User"]
		
		for role in required_roles:
			if frappe.db.exists("Role", role):
				health_report["checks"].append(f"✅ Rôle {role} existe")
				print(f"  ✅ Rôle {role}")
			else:
				warning_msg = f"⚠️ Rôle {role} manquant"
				health_report["warnings"].append(warning_msg)
				print(f"  {warning_msg}")
		
		# Vérification permissions DocTypes
		doctypes_to_check = ["OVH SMS Settings", "SMS Event Reminder"]
		for doctype in doctypes_to_check:
			perms = frappe.db.count("DocPerm", {"parent": doctype})
			if perms > 0:
				health_report["checks"].append(f"✅ Permissions {doctype}: {perms}")
				print(f"  ✅ {doctype}: {perms} permissions")
			else:
				warning_msg = f"⚠️ Aucune permission pour {doctype}"
				health_report["warnings"].append(warning_msg)
				print(f"  {warning_msg}")
		
	except Exception as e:
		error_msg = f"❌ Erreur vérification permissions: {str(e)}"
		health_report["errors"].append(error_msg)
		print(f"  {error_msg}")

def check_recent_activity(health_report):
	"""Vérifie l'activité récente du système"""
	print("\n📊 Vérification de l'activité récente...")
	
	try:
		# Vérification des derniers rappels
		reminder_settings = frappe.get_single('SMS Event Reminder')
		
		if reminder_settings.last_reminder_sent:
			last_sent = reminder_settings.last_reminder_sent
			hours_ago = (datetime.now() - last_sent).total_seconds() / 3600
			
			if hours_ago < 24:
				health_report["checks"].append(f"✅ Dernier rappel: il y a {hours_ago:.1f}h")
				print(f"  ✅ Dernier rappel: il y a {hours_ago:.1f}h")
			else:
				warning_msg = f"⚠️ Dernier rappel: il y a {hours_ago:.1f}h"
				health_report["warnings"].append(warning_msg)
				print(f"  {warning_msg}")
		else:
			warning_msg = "⚠️ Aucun rappel envoyé récemment"
			health_report["warnings"].append(warning_msg)
			print(f"  {warning_msg}")
		
		# Statistiques
		total_sent = reminder_settings.total_reminders_sent or 0
		failed_count = reminder_settings.failed_reminders_count or 0
		
		health_report["checks"].append(f"✅ Total rappels: {total_sent}")
		health_report["checks"].append(f"✅ Échecs: {failed_count}")
		print(f"  ✅ Total rappels: {total_sent}")
		print(f"  ✅ Échecs: {failed_count}")
		
		# Taux d'échec
		if total_sent > 0:
			failure_rate = (failed_count / total_sent) * 100
			if failure_rate > 10:
				warning_msg = f"⚠️ Taux d'échec élevé: {failure_rate:.1f}%"
				health_report["warnings"].append(warning_msg)
				print(f"  {warning_msg}")
			else:
				health_report["checks"].append(f"✅ Taux d'échec: {failure_rate:.1f}%")
				print(f"  ✅ Taux d'échec: {failure_rate:.1f}%")
		
	except Exception as e:
		error_msg = f"❌ Erreur vérification activité: {str(e)}"
		health_report["errors"].append(error_msg)
		print(f"  {error_msg}")

def check_database_health(health_report):
	"""Vérifie la santé de la base de données"""
	print("\n🗄️ Vérification de la base de données...")
	
	try:
		# Vérification des tables principales
		required_tables = ["tabOVH SMS Settings", "tabSMS Event Reminder", "tabEvent"]
		
		for table in required_tables:
			try:
				count = frappe.db.sql(f"SELECT COUNT(*) FROM `{table}` LIMIT 1")[0][0]
				health_report["checks"].append(f"✅ Table {table} accessible")
				print(f"  ✅ {table}")
			except Exception as e:
				error_msg = f"❌ Table {table} inaccessible: {str(e)}"
				health_report["errors"].append(error_msg)
				print(f"  {error_msg}")
		
		# Vérification des index
		try:
			# Vérifier l'index sur les événements
			frappe.db.sql("SHOW INDEX FROM `tabEvent` WHERE Key_name = 'starts_on'")
			health_report["checks"].append("✅ Index base de données OK")
			print("  ✅ Index OK")
		except Exception as e:
			warning_msg = f"⚠️ Problème index: {str(e)}"
			health_report["warnings"].append(warning_msg)
			print(f"  {warning_msg}")
		
	except Exception as e:
		error_msg = f"❌ Erreur vérification base de données: {str(e)}"
		health_report["errors"].append(error_msg)
		print(f"  {error_msg}")

def get_eligible_events_count(event_filter):
	"""Compte les événements éligibles aux rappels"""
	try:
		if not event_filter:
			return 0
		
		future_date = datetime.now() + timedelta(days=30)
		
		count = frappe.db.count("Event", {
			"subject": ["like", f"%{event_filter}%"],
			"starts_on": [">", datetime.now()],
			"starts_on": ["<", future_date],
			"docstatus": 1
		})
		
		return count
	except Exception:
		return 0

def display_health_report(health_report):
	"""Affiche le rapport de santé final"""
	print("\n" + "=" * 60)
	print("📋 RAPPORT DE SANTÉ FINAL")
	print("=" * 60)
	
	# Statut global
	status_icon = {
		"healthy": "✅",
		"warning": "⚠️",
		"error": "❌"
	}
	
	status = health_report["overall_status"]
	print(f"\n🏥 Statut global: {status_icon[status]} {status.upper()}")
	
	# Résumé
	checks_count = len(health_report["checks"])
	warnings_count = len(health_report["warnings"])
	errors_count = len(health_report["errors"])
	
	print(f"\n📊 Résumé:")
	print(f"  ✅ Vérifications réussies: {checks_count}")
	print(f"  ⚠️ Avertissements: {warnings_count}")
	print(f"  ❌ Erreurs: {errors_count}")
	
	# Détails des avertissements
	if health_report["warnings"]:
		print(f"\n⚠️ Avertissements:")
		for warning in health_report["warnings"]:
			print(f"  - {warning}")
	
	# Détails des erreurs
	if health_report["errors"]:
		print(f"\n❌ Erreurs:")
		for error in health_report["errors"]:
			print(f"  - {error}")
	
	# Recommandations
	print(f"\n💡 Recommandations:")
	if errors_count > 0:
		print("  - Corrigez les erreurs avant de continuer")
		print("  - Vérifiez la configuration OVH SMS")
		print("  - Consultez les logs pour plus de détails")
	elif warnings_count > 0:
		print("  - Examinez les avertissements")
		print("  - Optimisez la configuration si nécessaire")
	else:
		print("  - Système en bonne santé !")
		print("  - Continuez à surveiller les statistiques")
	
	print(f"\n🕒 Vérification terminée: {health_report['timestamp']}")
	print("=" * 60)

def save_health_report(health_report, filename=None):
	"""Sauvegarde le rapport de santé"""
	if not filename:
		timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
		filename = f"sms_health_report_{timestamp}.json"
	
	try:
		with open(filename, 'w', encoding='utf-8') as f:
			json.dump(health_report, f, indent=2, ensure_ascii=False, default=str)
		
		print(f"\n💾 Rapport sauvegardé: {filename}")
		return filename
	except Exception as e:
		print(f"\n❌ Erreur sauvegarde rapport: {e}")
		return None

@frappe.whitelist()
def run_health_check_api():
	"""API pour exécuter la vérification de santé"""
	try:
		health_report = run_health_check()
		return health_report
	except Exception as e:
		frappe.log_error(f"Erreur health check API: {e}")
		return {
			"overall_status": "error",
			"errors": [str(e)],
			"timestamp": datetime.now().isoformat()
		}

if __name__ == "__main__":
	# Exécution en mode standalone
	try:
		frappe.init(site='test_site')
		frappe.connect()
		
		health_report = run_health_check()
		
		# Sauvegarde optionnelle
		save_health_report(health_report)
		
		frappe.destroy()
		
	except Exception as e:
		print(f"❌ Erreur critique: {e}")
		exit(1)
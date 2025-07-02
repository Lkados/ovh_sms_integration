# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import unittest
import frappe
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

class TestSMSEventReminder(unittest.TestCase):
	
	def setUp(self):
		"""Configuration initiale pour chaque test"""
		self.test_customer = None
		self.test_employee = None
		self.test_event = None
		self.reminder_settings = None
		
		# Création de données de test
		self.create_test_data()
	
	def tearDown(self):
		"""Nettoyage après chaque test"""
		self.cleanup_test_data()
	
	def create_test_data(self):
		"""Crée les données de test nécessaires"""
		try:
			# Création d'un client de test
			if not frappe.db.exists("Customer", "Test Customer SMS"):
				self.test_customer = frappe.get_doc({
					"doctype": "Customer",
					"customer_name": "Test Customer SMS",
					"customer_type": "Individual",
					"customer_group": "Individual",
					"territory": "France",
					"mobile_no": "+33123456789"
				})
				self.test_customer.insert()
			else:
				self.test_customer = frappe.get_doc("Customer", "Test Customer SMS")
			
			# Création d'un employé de test
			if not frappe.db.exists("Employee", {"employee_name": "Test Employee SMS"}):
				self.test_employee = frappe.get_doc({
					"doctype": "Employee",
					"employee_name": "Test Employee SMS",
					"first_name": "Test",
					"last_name": "Employee",
					"cell_number": "+33987654321",
					"status": "Active",
					"company": frappe.get_all("Company", limit=1)[0].name if frappe.get_all("Company") else None
				})
				if self.test_employee.company:
					self.test_employee.insert()
			else:
				employees = frappe.get_all("Employee", filters={"employee_name": "Test Employee SMS"}, limit=1)
				if employees:
					self.test_employee = frappe.get_doc("Employee", employees[0].name)
			
			# Configuration des paramètres de rappel
			self.reminder_settings = frappe.get_single('SMS Event Reminder')
			self.reminder_settings.enabled = 1
			self.reminder_settings.event_type_filter = "entretien"
			self.reminder_settings.reminder_hours_before = 24
			self.reminder_settings.send_to_customer_only = 1
			self.reminder_settings.send_to_employee = 0
			self.reminder_settings.save()
			
		except Exception as e:
			frappe.log_error(f"Erreur création données test: {e}")
	
	def cleanup_test_data(self):
		"""Nettoie les données de test"""
		try:
			# Suppression de l'événement de test
			if self.test_event and frappe.db.exists("Event", self.test_event.name):
				frappe.delete_doc("Event", self.test_event.name, force=1)
			
			# Suppression du client de test
			if self.test_customer and frappe.db.exists("Customer", self.test_customer.name):
				frappe.delete_doc("Customer", self.test_customer.name, force=1)
			
			# Suppression de l'employé de test
			if self.test_employee and frappe.db.exists("Employee", self.test_employee.name):
				frappe.delete_doc("Employee", self.test_employee.name, force=1)
				
		except Exception as e:
			frappe.log_error(f"Erreur nettoyage données test: {e}")
	
	def create_test_event(self, hours_from_now=24):
		"""Crée un événement de test"""
		start_time = datetime.now() + timedelta(hours=hours_from_now)
		end_time = start_time + timedelta(hours=1)
		
		self.test_event = frappe.get_doc({
			"doctype": "Event",
			"subject": "Test entretien SMS",
			"description": "Événement de test pour les rappels SMS",
			"starts_on": start_time,
			"ends_on": end_time,
			"event_type": "Private",
			"event_participants": [
				{
					"reference_doctype": "Customer",
					"reference_docname": self.test_customer.name
				}
			]
		})
		self.test_event.insert()
		self.test_event.submit()
		return self.test_event
	
	def test_reminder_settings_validation(self):
		"""Test de validation des paramètres de rappel"""
		# Test avec paramètres valides
		self.reminder_settings.enabled = 1
		self.reminder_settings.event_type_filter = "entretien"
		self.reminder_settings.reminder_hours_before = 24
		
		try:
			self.reminder_settings.validate()
			self.assertTrue(True, "Validation réussie avec paramètres valides")
		except Exception as e:
			self.fail(f"Validation échouée avec paramètres valides: {e}")
		
		# Test avec paramètres invalides
		self.reminder_settings.reminder_hours_before = -1
		
		with self.assertRaises(Exception):
			self.reminder_settings.validate()
	
	def test_reminder_times_parsing(self):
		"""Test du parsing des heures de rappel multiples"""
		# Test avec rappels multiples
		self.reminder_settings.enable_multiple_reminders = 1
		self.reminder_settings.reminder_times = "24,2,0.5"
		
		times = self.reminder_settings.get_reminder_times()
		expected_times = [24.0, 2.0, 0.5]
		
		self.assertEqual(times, expected_times, "Parsing des heures de rappel incorrect")
		
		# Test avec rappel simple
		self.reminder_settings.enable_multiple_reminders = 0
		self.reminder_settings.reminder_hours_before = 48
		
		times = self.reminder_settings.get_reminder_times()
		expected_times = [48.0]
		
		self.assertEqual(times, expected_times, "Rappel simple incorrect")
	
	def test_message_template_formatting(self):
		"""Test du formatage des templates de message"""
		event = self.create_test_event()
		
		template = "Rappel: {{subject}} le {{start_date}} à {{start_time}} pour {{customer_name}}"
		
		formatted_message = self.reminder_settings.format_message(
			template, 
			event, 
			customer_name="Test Customer"
		)
		
		self.assertIn("Test entretien SMS", formatted_message)
		self.assertIn("Test Customer", formatted_message)
		self.assertNotIn("{{", formatted_message, "Variables non remplacées dans le template")
	
	def test_phone_number_validation(self):
		"""Test de validation des numéros de téléphone"""
		from ovh_sms_integration.utils.sms_utils import validate_phone_number
		
		# Test avec numéro français
		phone = validate_phone_number("0123456789")
		self.assertEqual(phone, "+33123456789", "Format numéro français incorrect")
		
		# Test avec numéro international
		phone = validate_phone_number("+33123456789")
		self.assertEqual(phone, "+33123456789", "Numéro international modifié")
		
		# Test avec numéro invalide
		with self.assertRaises(ValueError):
			validate_phone_number("invalid")
	
	def test_event_filtering(self):
		"""Test du filtrage des événements"""
		# Création d'événements test
		event_entretien = self.create_test_event(24)  # Dans 24h
		
		# Événement sans le mot-clé
		event_autre = frappe.get_doc({
			"doctype": "Event",
			"subject": "Réunion équipe",
			"starts_on": datetime.now() + timedelta(hours=24),
			"ends_on": datetime.now() + timedelta(hours=25),
			"event_type": "Private"
		})
		event_autre.insert()
		event_autre.submit()
		
		# Test de récupération des événements
		events = self.reminder_settings.get_events_for_reminder()
		
		# Vérifier que seul l'événement avec "entretien" est retourné
		event_subjects = [e.subject for e in events]
		self.assertIn("Test entretien SMS", event_subjects)
		self.assertNotIn("Réunion équipe", event_subjects)
		
		# Nettoyage
		frappe.delete_doc("Event", event_autre.name, force=1)
	
	def test_business_hours_check(self):
		"""Test de vérification des heures ouvrables"""
		# Configuration heures ouvrables
		self.reminder_settings.business_hours_only = 1
		self.reminder_settings.business_start_time = "09:00:00"
		self.reminder_settings.business_end_time = "18:00:00"
		self.reminder_settings.exclude_weekends = 0
		
		# Mock de l'heure actuelle pour tester
		with patch('ovh_sms_integration.ovh_sms_integration.doctype.sms_event_reminder.sms_event_reminder.datetime') as mock_datetime:
			# Test pendant les heures ouvrables (14h un mardi)
			mock_datetime.now.return_value = datetime(2024, 1, 16, 14, 0, 0)  # Mardi 14h
			mock_datetime.now.return_value.time.return_value = datetime(2024, 1, 16, 14, 0, 0).time()
			mock_datetime.now.return_value.weekday.return_value = 1  # Mardi
			
			self.assertTrue(self.reminder_settings.should_send_now(), "Devrait envoyer pendant les heures ouvrables")
			
			# Test en dehors des heures ouvrables (22h)
			mock_datetime.now.return_value = datetime(2024, 1, 16, 22, 0, 0)  # Mardi 22h
			mock_datetime.now.return_value.time.return_value = datetime(2024, 1, 16, 22, 0, 0).time()
			
			self.assertFalse(self.reminder_settings.should_send_now(), "Ne devrait pas envoyer hors heures ouvrables")
	
	def test_contact_mobile_extraction(self):
		"""Test d'extraction des numéros mobiles"""
		# Test avec client
		mobile = self.reminder_settings.get_customer_mobile(self.test_customer)
		self.assertEqual(mobile, "+33123456789", "Mobile client non extrait correctement")
		
		# Test avec employé
		if self.test_employee:
			mobile = self.reminder_settings.get_employee_mobile(self.test_employee)
			self.assertEqual(mobile, "+33987654321", "Mobile employé non extrait correctement")
	
	@patch('ovh_sms_integration.ovh_sms_integration.doctype.sms_event_reminder.sms_event_reminder.send_sms')
	def test_sms_sending_mock(self, mock_send_sms):
		"""Test d'envoi SMS avec mock"""
		# Configuration du mock
		mock_send_sms.return_value = {
			"success": True,
			"message": "SMS envoyé avec succès"
		}
		
		event = self.create_test_event()
		
		# Test d'envoi
		result = self.reminder_settings.send_sms_reminder(
			"Message de test", 
			"+33123456789"
		)
		
		# Vérifications
		self.assertTrue(mock_send_sms.called, "Fonction send_sms non appelée")
		self.assertTrue(result["success"], "Envoi SMS échoué")
		
		# Vérifier les paramètres passés
		call_args = mock_send_sms.call_args
		self.assertEqual(call_args[0][0], "Message de test", "Message incorrect")
		self.assertEqual(call_args[0][1], "+33123456789", "Numéro incorrect")
	
	def test_statistics_update(self):
		"""Test de mise à jour des statistiques"""
		initial_count = self.reminder_settings.total_reminders_sent or 0
		
		# Simulation d'envoi de rappels
		self.reminder_settings.update_statistics(5, 1)
		
		# Recharger les données
		self.reminder_settings.reload()
		
		# Vérifications
		self.assertEqual(
			self.reminder_settings.total_reminders_sent, 
			initial_count + 5, 
			"Compteur total incorrect"
		)
		self.assertEqual(
			self.reminder_settings.failed_reminders_count, 
			1, 
			"Compteur échecs incorrect"
		)
	
	def test_template_selection(self):
		"""Test de sélection des templates"""
		# Configuration des templates
		self.reminder_settings.customer_template = "Template client: {{subject}}"
		self.reminder_settings.employee_template = "Template employé: {{subject}}"
		self.reminder_settings.default_template = "Template par défaut: {{subject}}"
		
		# Test sélection template client
		template = self.reminder_settings.get_message_template("customer")
		self.assertEqual(template, "Template client: {{subject}}")
		
		# Test sélection template employé
		template = self.reminder_settings.get_message_template("employee")
		self.assertEqual(template, "Template employé: {{subject}}")
		
		# Test fallback vers template par défaut
		self.reminder_settings.customer_template = ""
		template = self.reminder_settings.get_message_template("customer")
		self.assertEqual(template, "Template par défaut: {{subject}}")

class TestSMSEventReminderIntegration(unittest.TestCase):
	"""Tests d'intégration avec les vraies données"""
	
	def setUp(self):
		"""Configuration pour tests d'intégration"""
		# Vérifier que l'environnement de test est prêt
		if not frappe.db.exists("Company"):
			self.skipTest("Aucune entreprise configurée pour les tests")
	
	def test_event_participant_extraction(self):
		"""Test d'extraction des participants d'événements réels"""
		# Ce test nécessite des données réelles dans la base
		# Il peut être ignoré dans certains environnements de test
		pass
	
	def test_scheduler_task_execution(self):
		"""Test d'exécution des tâches planifiées"""
		from ovh_sms_integration.tasks import check_event_reminders_hourly
		
		try:
			# Exécution de la tâche (sans envoi réel)
			check_event_reminders_hourly()
			self.assertTrue(True, "Tâche planifiée exécutée sans erreur")
		except Exception as e:
			self.fail(f"Erreur exécution tâche planifiée: {e}")

def run_all_tests():
	"""Exécute tous les tests"""
	loader = unittest.TestLoader()
	suite = unittest.TestSuite()
	
	# Ajouter les classes de test
	suite.addTests(loader.loadTestsFromTestCase(TestSMSEventReminder))
	suite.addTests(loader.loadTestsFromTestCase(TestSMSEventReminderIntegration))
	
	# Exécuter les tests
	runner = unittest.TextTestRunner(verbosity=2)
	result = runner.run(suite)
	
	return result.wasSuccessful()

if __name__ == '__main__':
	# Exécution des tests en mode standalone
	frappe.init(site='test_site')
	frappe.connect()
	
	success = run_all_tests()
	
	if success:
		print("✅ Tous les tests sont passés !")
	else:
		print("❌ Certains tests ont échoué")
	
	frappe.destroy()
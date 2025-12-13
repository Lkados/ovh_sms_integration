# -*- coding: utf-8 -*-
"""
Tests pour ovh_sms_integration.

Ce package contient:
- tests/test_standalone.py: Tests unitaires sans dépendance Frappe (46 tests)
- tests/test_sms_event_reminder.py: Tests d'intégration Frappe (existant)
- tests/unit/: Tests unitaires avec mocking Frappe

Pour exécuter les tests:
- Tests standalone: pytest ovh_sms_integration/tests/test_standalone.py
- Tests Frappe: bench --site [site] run-tests --app ovh_sms_integration
"""

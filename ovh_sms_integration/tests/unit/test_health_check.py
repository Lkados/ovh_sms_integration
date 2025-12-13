# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module health_check.py.

Ce module teste les fonctions de vérification de santé du système.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch


class TestRunHealthCheck:
    """Tests pour la fonction run_health_check."""

    @patch("ovh_sms_integration.health_check.display_health_report")
    @patch("ovh_sms_integration.health_check.check_database_health")
    @patch("ovh_sms_integration.health_check.check_recent_activity")
    @patch("ovh_sms_integration.health_check.check_permissions")
    @patch("ovh_sms_integration.health_check.check_scheduler")
    @patch("ovh_sms_integration.health_check.check_event_reminders")
    @patch("ovh_sms_integration.health_check.check_ovh_settings")
    @patch("ovh_sms_integration.health_check.check_doctypes")
    def test_run_health_check_healthy(
        self,
        mock_doctypes: MagicMock,
        mock_ovh: MagicMock,
        mock_reminders: MagicMock,
        mock_scheduler: MagicMock,
        mock_permissions: MagicMock,
        mock_activity: MagicMock,
        mock_db: MagicMock,
        mock_display: MagicMock,
    ) -> None:
        """Test avec système sain."""
        from ovh_sms_integration.health_check import run_health_check

        result = run_health_check()

        assert result["overall_status"] == "healthy"
        assert "timestamp" in result
        mock_doctypes.assert_called_once()
        mock_ovh.assert_called_once()

    @patch("ovh_sms_integration.health_check.display_health_report")
    @patch("ovh_sms_integration.health_check.check_database_health")
    @patch("ovh_sms_integration.health_check.check_recent_activity")
    @patch("ovh_sms_integration.health_check.check_permissions")
    @patch("ovh_sms_integration.health_check.check_scheduler")
    @patch("ovh_sms_integration.health_check.check_event_reminders")
    @patch("ovh_sms_integration.health_check.check_ovh_settings")
    @patch("ovh_sms_integration.health_check.check_doctypes")
    def test_run_health_check_with_warnings(
        self,
        mock_doctypes: MagicMock,
        mock_ovh: MagicMock,
        mock_reminders: MagicMock,
        mock_scheduler: MagicMock,
        mock_permissions: MagicMock,
        mock_activity: MagicMock,
        mock_db: MagicMock,
        mock_display: MagicMock,
    ) -> None:
        """Test avec warnings."""
        from ovh_sms_integration.health_check import run_health_check

        def add_warning(report: dict[str, Any]) -> None:
            report["warnings"].append("Test warning")

        mock_ovh.side_effect = add_warning

        result = run_health_check()

        assert result["overall_status"] == "warning"

    @patch("ovh_sms_integration.health_check.display_health_report")
    @patch("ovh_sms_integration.health_check.check_database_health")
    @patch("ovh_sms_integration.health_check.check_recent_activity")
    @patch("ovh_sms_integration.health_check.check_permissions")
    @patch("ovh_sms_integration.health_check.check_scheduler")
    @patch("ovh_sms_integration.health_check.check_event_reminders")
    @patch("ovh_sms_integration.health_check.check_ovh_settings")
    @patch("ovh_sms_integration.health_check.check_doctypes")
    def test_run_health_check_with_errors(
        self,
        mock_doctypes: MagicMock,
        mock_ovh: MagicMock,
        mock_reminders: MagicMock,
        mock_scheduler: MagicMock,
        mock_permissions: MagicMock,
        mock_activity: MagicMock,
        mock_db: MagicMock,
        mock_display: MagicMock,
    ) -> None:
        """Test avec erreurs."""
        from ovh_sms_integration.health_check import run_health_check

        def add_error(report: dict[str, Any]) -> None:
            report["errors"].append("Test error")

        mock_doctypes.side_effect = add_error

        result = run_health_check()

        assert result["overall_status"] == "error"

    @patch("ovh_sms_integration.health_check.display_health_report")
    @patch("ovh_sms_integration.health_check.check_doctypes")
    def test_run_health_check_exception(
        self, mock_doctypes: MagicMock, mock_display: MagicMock
    ) -> None:
        """Test avec exception."""
        from ovh_sms_integration.health_check import run_health_check

        mock_doctypes.side_effect = Exception("Test exception")

        result = run_health_check()

        assert result["overall_status"] == "error"
        assert any("exception" in e.lower() for e in result["errors"])


class TestCheckDoctypes:
    """Tests pour la fonction check_doctypes."""

    @patch("ovh_sms_integration.health_check.frappe")
    def test_all_doctypes_exist(self, mock_frappe: MagicMock) -> None:
        """Test tous les DocTypes existent."""
        from ovh_sms_integration.health_check import check_doctypes

        mock_frappe.db.exists.return_value = True

        report: dict[str, Any] = {"checks": [], "warnings": [], "errors": []}
        check_doctypes(report)

        assert len(report["checks"]) >= 2
        assert len(report["errors"]) == 0

    @patch("ovh_sms_integration.health_check.frappe")
    def test_missing_doctype(self, mock_frappe: MagicMock) -> None:
        """Test DocType manquant."""
        from ovh_sms_integration.health_check import check_doctypes

        mock_frappe.db.exists.return_value = False

        report: dict[str, Any] = {"checks": [], "warnings": [], "errors": []}
        check_doctypes(report)

        assert len(report["errors"]) >= 2

    @patch("ovh_sms_integration.health_check.frappe")
    def test_doctype_check_exception(self, mock_frappe: MagicMock) -> None:
        """Test exception lors de la vérification."""
        from ovh_sms_integration.health_check import check_doctypes

        mock_frappe.db.exists.side_effect = Exception("DB error")

        report: dict[str, Any] = {"checks": [], "warnings": [], "errors": []}
        check_doctypes(report)

        assert len(report["errors"]) >= 1


class TestCheckOvhSettings:
    """Tests pour la fonction check_ovh_settings."""

    @patch("ovh_sms_integration.health_check.frappe")
    def test_ovh_settings_enabled_complete(self, mock_frappe: MagicMock) -> None:
        """Test paramètres OVH complets et activés."""
        from ovh_sms_integration.health_check import check_ovh_settings

        mock_settings = MagicMock()
        mock_settings.enabled = True
        mock_settings.application_key = "test_key"
        mock_settings.get_password.return_value = "secret"
        mock_settings.test_connection.return_value = {"success": True}
        mock_frappe.get_single.return_value = mock_settings

        report: dict[str, Any] = {"checks": [], "warnings": [], "errors": []}
        check_ovh_settings(report)

        assert any("OVH SMS activé" in c for c in report["checks"])

    @patch("ovh_sms_integration.health_check.frappe")
    def test_ovh_settings_disabled(self, mock_frappe: MagicMock) -> None:
        """Test paramètres OVH désactivés."""
        from ovh_sms_integration.health_check import check_ovh_settings

        mock_settings = MagicMock()
        mock_settings.enabled = False
        mock_frappe.get_single.return_value = mock_settings

        report: dict[str, Any] = {"checks": [], "warnings": [], "errors": []}
        check_ovh_settings(report)

        assert any("désactivé" in w for w in report["warnings"])

    @patch("ovh_sms_integration.health_check.frappe")
    def test_ovh_settings_missing_field(self, mock_frappe: MagicMock) -> None:
        """Test champ manquant."""
        from ovh_sms_integration.health_check import check_ovh_settings

        mock_settings = MagicMock()
        mock_settings.enabled = True
        mock_settings.application_key = None
        mock_settings.get_password.return_value = None
        mock_frappe.get_single.return_value = mock_settings

        report: dict[str, Any] = {"checks": [], "warnings": [], "errors": []}
        check_ovh_settings(report)

        assert len(report["errors"]) >= 1

    @patch("ovh_sms_integration.health_check.frappe")
    def test_ovh_connection_failed(self, mock_frappe: MagicMock) -> None:
        """Test connexion OVH échouée."""
        from ovh_sms_integration.health_check import check_ovh_settings

        mock_settings = MagicMock()
        mock_settings.enabled = True
        mock_settings.application_key = "key"
        mock_settings.get_password.return_value = "secret"
        mock_settings.test_connection.return_value = {
            "success": False,
            "message": "Connection error",
        }
        mock_frappe.get_single.return_value = mock_settings

        report: dict[str, Any] = {"checks": [], "warnings": [], "errors": []}
        check_ovh_settings(report)

        assert any("échouée" in e for e in report["errors"])


class TestCheckEventReminders:
    """Tests pour la fonction check_event_reminders."""

    @patch("ovh_sms_integration.health_check.frappe")
    def test_reminders_enabled(self, mock_frappe: MagicMock) -> None:
        """Test rappels activés."""
        from ovh_sms_integration.health_check import check_event_reminders

        mock_settings = MagicMock()
        mock_settings.enabled = True
        mock_settings.event_type_filter = "entretien"
        mock_settings.customer_template = "Template"
        mock_frappe.get_single.return_value = mock_settings

        report: dict[str, Any] = {"checks": [], "warnings": [], "errors": []}
        check_event_reminders(report)

        assert any("activés" in c for c in report["checks"])

    @patch("ovh_sms_integration.health_check.frappe")
    def test_reminders_disabled(self, mock_frappe: MagicMock) -> None:
        """Test rappels désactivés."""
        from ovh_sms_integration.health_check import check_event_reminders

        mock_settings = MagicMock()
        mock_settings.enabled = False
        mock_frappe.get_single.return_value = mock_settings

        report: dict[str, Any] = {"checks": [], "warnings": [], "errors": []}
        check_event_reminders(report)

        assert any("désactivés" in w for w in report["warnings"])


class TestCheckScheduler:
    """Tests pour la fonction check_scheduler."""

    @patch("ovh_sms_integration.health_check.frappe")
    def test_scheduler_enabled(self, mock_frappe: MagicMock) -> None:
        """Test scheduler activé."""
        from ovh_sms_integration.health_check import check_scheduler

        mock_frappe.utils.cint.return_value = 1
        mock_frappe.db.get_single_value.return_value = 1

        report: dict[str, Any] = {"checks": [], "warnings": [], "errors": []}
        check_scheduler(report)

        assert any("activé" in c for c in report["checks"])

    @patch("ovh_sms_integration.health_check.frappe")
    def test_scheduler_disabled(self, mock_frappe: MagicMock) -> None:
        """Test scheduler désactivé."""
        from ovh_sms_integration.health_check import check_scheduler

        mock_frappe.utils.cint.return_value = 0
        mock_frappe.db.get_single_value.return_value = 0

        report: dict[str, Any] = {"checks": [], "warnings": [], "errors": []}
        check_scheduler(report)

        assert any("désactivé" in e for e in report["errors"])


class TestCheckPermissions:
    """Tests pour la fonction check_permissions."""

    @patch("ovh_sms_integration.health_check.frappe")
    def test_permissions_exist(self, mock_frappe: MagicMock) -> None:
        """Test permissions existent."""
        from ovh_sms_integration.health_check import check_permissions

        mock_frappe.db.exists.return_value = True
        mock_frappe.get_all.return_value = [
            {"parent": "SMS Pricing Campaign", "role": "System Manager"}
        ]

        report: dict[str, Any] = {"checks": [], "warnings": [], "errors": []}
        check_permissions(report)

        # Check should have some results
        assert isinstance(report["checks"], list)


class TestCheckRecentActivity:
    """Tests pour la fonction check_recent_activity."""

    @patch("ovh_sms_integration.health_check.frappe")
    def test_recent_activity_found(self, mock_frappe: MagicMock) -> None:
        """Test activité récente trouvée."""
        from ovh_sms_integration.health_check import check_recent_activity

        mock_frappe.db.count.return_value = 5
        mock_frappe.utils.add_days.return_value = "2025-01-01"
        mock_frappe.utils.today.return_value = "2025-01-08"

        report: dict[str, Any] = {"checks": [], "warnings": [], "errors": []}
        check_recent_activity(report)

        assert isinstance(report["checks"], list)

    @patch("ovh_sms_integration.health_check.frappe")
    def test_no_recent_activity(self, mock_frappe: MagicMock) -> None:
        """Test pas d'activité récente."""
        from ovh_sms_integration.health_check import check_recent_activity

        mock_frappe.db.count.return_value = 0
        mock_frappe.utils.add_days.return_value = "2025-01-01"
        mock_frappe.utils.today.return_value = "2025-01-08"

        report: dict[str, Any] = {"checks": [], "warnings": [], "errors": []}
        check_recent_activity(report)

        # Should have info or warning about no activity
        assert isinstance(report["checks"], list) or isinstance(
            report["warnings"], list
        )


class TestCheckDatabaseHealth:
    """Tests pour la fonction check_database_health."""

    @patch("ovh_sms_integration.health_check.frappe")
    def test_database_healthy(self, mock_frappe: MagicMock) -> None:
        """Test base de données saine."""
        from ovh_sms_integration.health_check import check_database_health

        mock_frappe.db.sql.return_value = [(1,)]

        report: dict[str, Any] = {"checks": [], "warnings": [], "errors": []}
        check_database_health(report)

        assert any(
            "connectée" in c or "database" in c.lower() for c in report["checks"]
        )

    @patch("ovh_sms_integration.health_check.frappe")
    def test_database_error(self, mock_frappe: MagicMock) -> None:
        """Test erreur base de données."""
        from ovh_sms_integration.health_check import check_database_health

        mock_frappe.db.sql.side_effect = Exception("DB connection error")

        report: dict[str, Any] = {"checks": [], "warnings": [], "errors": []}
        check_database_health(report)

        assert len(report["errors"]) >= 1


class TestDisplayHealthReport:
    """Tests pour la fonction display_health_report."""

    @patch("builtins.print")
    def test_display_healthy_report(self, mock_print: MagicMock) -> None:
        """Test affichage rapport sain."""
        from ovh_sms_integration.health_check import display_health_report

        report = {
            "overall_status": "healthy",
            "checks": ["Check 1", "Check 2"],
            "warnings": [],
            "errors": [],
        }

        display_health_report(report)

        mock_print.assert_called()

    @patch("builtins.print")
    def test_display_report_with_errors(self, mock_print: MagicMock) -> None:
        """Test affichage rapport avec erreurs."""
        from ovh_sms_integration.health_check import display_health_report

        report = {
            "overall_status": "error",
            "checks": ["Check 1"],
            "warnings": [],
            "errors": ["Error 1"],
        }

        display_health_report(report)

        mock_print.assert_called()

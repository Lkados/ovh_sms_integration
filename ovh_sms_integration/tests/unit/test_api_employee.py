# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module api/employee.py.

Ce module teste les API d'envoi de SMS aux employés.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch


class TestGetEmployeeMobile:
    """Tests pour la fonction get_employee_mobile."""

    @patch("ovh_sms_integration.api.employee.frappe")
    def test_get_employee_mobile_success(self, mock_frappe: MagicMock) -> None:
        """Test récupération mobile avec succès."""
        from ovh_sms_integration.api.employee import get_employee_mobile

        mock_frappe._ = lambda x: x
        mock_employee = MagicMock()
        mock_employee.cell_number = "+33612345678"
        mock_employee.employee_name = "Jean Dupont"
        mock_frappe.get_doc.return_value = mock_employee

        result = get_employee_mobile("EMP-001")

        assert result["status"] == "success"
        assert result["mobile"] == "+33612345678"
        assert result["employee_name"] == "Jean Dupont"

    @patch("ovh_sms_integration.api.employee.frappe")
    def test_get_employee_mobile_no_id(self, mock_frappe: MagicMock) -> None:
        """Test avec ID employé vide."""
        from ovh_sms_integration.api.employee import get_employee_mobile

        mock_frappe._ = lambda x: x

        result = get_employee_mobile("")

        assert result["status"] == "error"
        assert "requis" in result["message"]

    @patch("ovh_sms_integration.api.employee.frappe")
    def test_get_employee_mobile_no_phone(self, mock_frappe: MagicMock) -> None:
        """Test avec employé sans téléphone."""
        from ovh_sms_integration.api.employee import get_employee_mobile

        mock_frappe._ = lambda x: x.format("{0}") if "{0}" in x else x
        mock_employee = MagicMock()
        mock_employee.cell_number = None
        mock_employee.mobile_no = None
        mock_employee.personal_mobile = None
        mock_employee.mobile = None
        mock_employee.phone = None
        mock_employee.employee_name = "Jean Dupont"
        mock_frappe.get_doc.return_value = mock_employee

        result = get_employee_mobile("EMP-001")

        assert result["status"] == "error"
        assert "Jean Dupont" in result.get("employee_name", "")

    @patch("ovh_sms_integration.api.employee.frappe")
    def test_get_employee_mobile_not_found(self, mock_frappe: MagicMock) -> None:
        """Test avec employé introuvable."""
        from ovh_sms_integration.api.employee import get_employee_mobile

        mock_frappe._ = lambda x: x
        mock_frappe.DoesNotExistError = Exception
        mock_frappe.get_doc.side_effect = Exception("Not found")

        result = get_employee_mobile("EMP-999")

        assert result["status"] == "error"

    @patch("ovh_sms_integration.api.employee.frappe")
    def test_get_employee_mobile_fallback_fields(self, mock_frappe: MagicMock) -> None:
        """Test récupération via champs alternatifs."""
        from ovh_sms_integration.api.employee import get_employee_mobile

        mock_frappe._ = lambda x: x
        mock_employee = MagicMock()
        mock_employee.cell_number = None
        mock_employee.mobile_no = "+33698765432"
        mock_employee.employee_name = "Marie Martin"
        mock_frappe.get_doc.return_value = mock_employee

        result = get_employee_mobile("EMP-002")

        assert result["status"] == "success"
        assert result["mobile"] == "+33698765432"


class TestCheckSmsQuota:
    """Tests pour la fonction check_sms_quota."""

    @patch("ovh_sms_integration.api.employee.frappe")
    @patch("ovh_sms_integration.api.employee.check_user_sms_quota")
    def test_check_sms_quota_system_manager(
        self, mock_check_quota: MagicMock, mock_frappe: MagicMock
    ) -> None:
        """Test quota pour System Manager."""
        from ovh_sms_integration.api.employee import check_sms_quota

        mock_frappe._ = lambda x: x
        mock_frappe.session.user = "admin@test.com"
        mock_frappe.get_roles.return_value = ["System Manager"]
        mock_check_quota.return_value = 500

        result = check_sms_quota()

        assert result["status"] == "success"
        assert result["has_permission"] is True
        assert result["remaining"] == 500
        assert result["total"] == 9999

    @patch("ovh_sms_integration.api.employee.frappe")
    @patch("ovh_sms_integration.api.employee.check_user_sms_quota")
    def test_check_sms_quota_sms_manager(
        self, mock_check_quota: MagicMock, mock_frappe: MagicMock
    ) -> None:
        """Test quota pour SMS Manager."""
        from ovh_sms_integration.api.employee import check_sms_quota

        mock_frappe._ = lambda x: x
        mock_frappe.session.user = "manager@test.com"
        mock_frappe.get_roles.return_value = ["SMS Manager"]
        mock_check_quota.return_value = 200

        result = check_sms_quota()

        assert result["status"] == "success"
        assert result["total"] == 500

    @patch("ovh_sms_integration.api.employee.frappe")
    @patch("ovh_sms_integration.api.employee.check_user_sms_quota")
    def test_check_sms_quota_sms_user(
        self, mock_check_quota: MagicMock, mock_frappe: MagicMock
    ) -> None:
        """Test quota pour SMS User."""
        from ovh_sms_integration.api.employee import check_sms_quota

        mock_frappe._ = lambda x: x
        mock_frappe.session.user = "user@test.com"
        mock_frappe.get_roles.return_value = ["SMS User"]
        mock_check_quota.return_value = 50

        result = check_sms_quota()

        assert result["status"] == "success"
        assert result["total"] == 100

    @patch("ovh_sms_integration.api.employee.frappe")
    @patch("ovh_sms_integration.api.employee.check_user_sms_quota")
    def test_check_sms_quota_no_permission(
        self, mock_check_quota: MagicMock, mock_frappe: MagicMock
    ) -> None:
        """Test quota sans permission."""
        from ovh_sms_integration.api.employee import check_sms_quota

        mock_frappe._ = lambda x: x
        mock_frappe.session.user = "guest@test.com"
        mock_frappe.get_roles.return_value = ["Guest"]
        mock_check_quota.return_value = 0

        result = check_sms_quota()

        assert result["status"] == "success"
        assert result["has_permission"] is False
        assert result["total"] == 0

    @patch("ovh_sms_integration.api.employee.frappe")
    def test_check_sms_quota_import_error(self, mock_frappe: MagicMock) -> None:
        """Test avec erreur d'import."""
        mock_frappe._ = lambda x: x
        mock_frappe.session.user = "admin@test.com"

        with patch.dict(
            "sys.modules",
            {"ovh_sms_integration.permissions": None},
        ):
            with patch(
                "ovh_sms_integration.api.employee.check_user_sms_quota",
                side_effect=ImportError("Module not found"),
            ):
                from ovh_sms_integration.api.employee import check_sms_quota

                result = check_sms_quota()
                assert result["status"] == "error"


class TestSendSmsToEmployees:
    """Tests pour la fonction send_sms_to_employees."""

    @patch("ovh_sms_integration.api.employee.frappe")
    @patch("ovh_sms_integration.api.employee.check_user_sms_quota")
    @patch("ovh_sms_integration.api.employee.send_sms")
    @patch("ovh_sms_integration.api.employee.get_employee_mobile")
    def test_send_sms_to_single_employee_success(
        self,
        mock_get_mobile: MagicMock,
        mock_send_sms: MagicMock,
        mock_check_quota: MagicMock,
        mock_frappe: MagicMock,
    ) -> None:
        """Test envoi SMS à un employé avec succès."""
        from ovh_sms_integration.api.employee import send_sms_to_employees

        mock_frappe._ = lambda x: x
        mock_frappe.session.user = "admin@test.com"
        mock_frappe.get_value.return_value = "Admin User"
        mock_check_quota.return_value = 100
        mock_get_mobile.return_value = {
            "status": "success",
            "mobile": "+33612345678",
            "employee_name": "Jean Dupont",
        }
        mock_send_sms.return_value = {"success": True, "details": {"ids": ["123"]}}

        result = send_sms_to_employees("EMP-001", "Message de test")

        assert result["status"] == "success"
        assert result["sent"] == 1
        assert result["failed"] == 0

    @patch("ovh_sms_integration.api.employee.frappe")
    @patch("ovh_sms_integration.api.employee.check_user_sms_quota")
    @patch("ovh_sms_integration.api.employee.send_sms")
    @patch("ovh_sms_integration.api.employee.get_employee_mobile")
    def test_send_sms_to_multiple_employees(
        self,
        mock_get_mobile: MagicMock,
        mock_send_sms: MagicMock,
        mock_check_quota: MagicMock,
        mock_frappe: MagicMock,
    ) -> None:
        """Test envoi SMS à plusieurs employés."""
        from ovh_sms_integration.api.employee import send_sms_to_employees

        mock_frappe._ = lambda x: x
        mock_frappe.session.user = "admin@test.com"
        mock_frappe.get_value.return_value = "Admin User"
        mock_check_quota.return_value = 100
        mock_get_mobile.side_effect = [
            {"status": "success", "mobile": "+33612345678", "employee_name": "Jean"},
            {"status": "success", "mobile": "+33698765432", "employee_name": "Marie"},
        ]
        mock_send_sms.return_value = {"success": True, "details": {"ids": ["123"]}}

        result = send_sms_to_employees(
            json.dumps(["EMP-001", "EMP-002"]), "Message de test"
        )

        assert result["status"] == "success"
        assert result["total"] == 2
        assert result["sent"] == 2

    @patch("ovh_sms_integration.api.employee.frappe")
    @patch("ovh_sms_integration.api.employee.check_user_sms_quota")
    def test_send_sms_insufficient_quota(
        self, mock_check_quota: MagicMock, mock_frappe: MagicMock
    ) -> None:
        """Test avec quota insuffisant."""
        from ovh_sms_integration.api.employee import send_sms_to_employees

        mock_frappe._ = lambda x: x
        mock_frappe.session.user = "admin@test.com"
        mock_check_quota.return_value = 1  # Seulement 1 SMS disponible

        result = send_sms_to_employees(
            json.dumps(["EMP-001", "EMP-002", "EMP-003"]), "Message"
        )

        assert result["status"] == "error"
        assert "insuffisant" in result["message"]

    @patch("ovh_sms_integration.api.employee.frappe")
    def test_send_sms_empty_message(self, mock_frappe: MagicMock) -> None:
        """Test avec message vide."""
        from ovh_sms_integration.api.employee import send_sms_to_employees

        mock_frappe._ = lambda x: x
        mock_frappe.session.user = "admin@test.com"

        with patch(
            "ovh_sms_integration.api.employee.check_user_sms_quota", return_value=100
        ):
            result = send_sms_to_employees("EMP-001", "")

            assert result["status"] == "error"
            assert "vide" in result["message"]

    @patch("ovh_sms_integration.api.employee.frappe")
    def test_send_sms_no_employees(self, mock_frappe: MagicMock) -> None:
        """Test sans employés sélectionnés."""
        from ovh_sms_integration.api.employee import send_sms_to_employees

        mock_frappe._ = lambda x: x

        result = send_sms_to_employees("[]", "Message")

        assert result["status"] == "error"
        assert "Aucun employé" in result["message"]

    @patch("ovh_sms_integration.api.employee.frappe")
    def test_send_sms_invalid_format(self, mock_frappe: MagicMock) -> None:
        """Test avec format d'IDs invalide."""
        from ovh_sms_integration.api.employee import send_sms_to_employees

        mock_frappe._ = lambda x: x

        result = send_sms_to_employees(123, "Message")  # type: ignore

        assert result["status"] == "error"


class TestGetEmployeesWithMobile:
    """Tests pour la fonction get_employees_with_mobile."""

    @patch("ovh_sms_integration.api.employee.frappe")
    def test_get_employees_with_mobile_success(self, mock_frappe: MagicMock) -> None:
        """Test récupération liste employés avec mobile."""
        from ovh_sms_integration.api.employee import get_employees_with_mobile

        mock_frappe._ = lambda x: x
        mock_frappe.get_all.return_value = [
            {"name": "EMP-001", "employee_name": "Jean", "designation": "Tech"},
            {"name": "EMP-002", "employee_name": "Marie", "designation": "Admin"},
        ]

        mock_emp1 = MagicMock()
        mock_emp1.name = "EMP-001"
        mock_emp1.employee_name = "Jean"
        mock_emp1.cell_number = "+33612345678"
        mock_emp1.designation = "Tech"

        mock_emp2 = MagicMock()
        mock_emp2.name = "EMP-002"
        mock_emp2.employee_name = "Marie"
        mock_emp2.cell_number = None
        mock_emp2.mobile_no = None
        mock_emp2.personal_mobile = None
        mock_emp2.mobile = None
        mock_emp2.phone = None
        mock_emp2.designation = "Admin"

        mock_frappe.get_doc.side_effect = [mock_emp1, mock_emp2]

        result = get_employees_with_mobile()

        assert result["status"] == "success"
        assert result["total"] == 1  # Seulement Jean a un mobile
        assert len(result["employees"]) == 1

    @patch("ovh_sms_integration.api.employee.frappe")
    def test_get_employees_with_mobile_error(self, mock_frappe: MagicMock) -> None:
        """Test avec erreur base de données."""
        from ovh_sms_integration.api.employee import get_employees_with_mobile

        mock_frappe._ = lambda x: x
        mock_frappe.get_all.side_effect = Exception("DB Error")
        mock_frappe.log_error = MagicMock()

        result = get_employees_with_mobile()

        assert result["status"] == "error"

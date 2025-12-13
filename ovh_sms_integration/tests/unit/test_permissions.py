# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module permissions.py.

Ce module teste les permissions, quotas, et la sécurité SMS.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestGetCampaignPermissionQueryConditions:
    """Tests pour get_campaign_permission_query_conditions."""

    @patch("ovh_sms_integration.permissions.frappe")
    def test_system_manager_sees_all(self, mock_frappe: MagicMock) -> None:
        """System Manager voit toutes les campagnes."""
        from ovh_sms_integration.permissions import (
            get_campaign_permission_query_conditions,
        )

        mock_frappe.session.user = "admin@test.com"
        mock_frappe.get_roles.return_value = ["System Manager"]

        result = get_campaign_permission_query_conditions()

        assert result == ""

    @patch("ovh_sms_integration.permissions.frappe")
    def test_sms_manager_sees_company_campaigns(self, mock_frappe: MagicMock) -> None:
        """SMS Manager voit les campagnes de sa société."""
        from ovh_sms_integration.permissions import (
            get_campaign_permission_query_conditions,
        )

        mock_frappe.session.user = "manager@test.com"
        mock_frappe.get_roles.return_value = ["SMS Manager"]
        mock_frappe.db.get_value.return_value = "Test Company"

        result = get_campaign_permission_query_conditions()

        assert "Test Company" in result
        assert "company" in result

    @patch("ovh_sms_integration.permissions.frappe")
    def test_sms_manager_no_company(self, mock_frappe: MagicMock) -> None:
        """SMS Manager sans société voit toutes les campagnes."""
        from ovh_sms_integration.permissions import (
            get_campaign_permission_query_conditions,
        )

        mock_frappe.session.user = "manager@test.com"
        mock_frappe.get_roles.return_value = ["SMS Manager"]
        mock_frappe.db.get_value.return_value = None

        result = get_campaign_permission_query_conditions()

        assert result == ""

    @patch("ovh_sms_integration.permissions.frappe")
    def test_sms_user_sees_own_campaigns(self, mock_frappe: MagicMock) -> None:
        """SMS User voit seulement ses propres campagnes."""
        from ovh_sms_integration.permissions import (
            get_campaign_permission_query_conditions,
        )

        mock_frappe.session.user = "user@test.com"
        mock_frappe.get_roles.return_value = ["SMS User"]

        result = get_campaign_permission_query_conditions()

        assert "owner = 'user@test.com'" in result

    @patch("ovh_sms_integration.permissions.frappe")
    def test_no_permission_guest(self, mock_frappe: MagicMock) -> None:
        """Guest n'a pas accès."""
        from ovh_sms_integration.permissions import (
            get_campaign_permission_query_conditions,
        )

        mock_frappe.session.user = "guest@test.com"
        mock_frappe.get_roles.return_value = ["Guest"]

        result = get_campaign_permission_query_conditions()

        assert result == "1=0"

    @patch("ovh_sms_integration.permissions.frappe")
    def test_with_explicit_user(self, mock_frappe: MagicMock) -> None:
        """Test avec utilisateur explicite."""
        from ovh_sms_integration.permissions import (
            get_campaign_permission_query_conditions,
        )

        mock_frappe.get_roles.return_value = ["System Manager"]

        result = get_campaign_permission_query_conditions("admin@example.com")

        assert result == ""
        mock_frappe.get_roles.assert_called_with("admin@example.com")


class TestHasCampaignPermission:
    """Tests pour has_campaign_permission."""

    @patch("ovh_sms_integration.permissions.frappe")
    def test_system_manager_has_permission(self, mock_frappe: MagicMock) -> None:
        """System Manager a toujours la permission."""
        from ovh_sms_integration.permissions import has_campaign_permission

        mock_frappe.session.user = "admin@test.com"
        mock_frappe.get_roles.return_value = ["System Manager"]

        mock_doc = MagicMock()
        mock_doc.owner = "other@test.com"
        mock_doc.company = "Other Company"

        result = has_campaign_permission(mock_doc)

        assert result is True

    @patch("ovh_sms_integration.permissions.frappe")
    def test_sms_manager_same_company(self, mock_frappe: MagicMock) -> None:
        """SMS Manager a accès aux campagnes de sa société."""
        from ovh_sms_integration.permissions import has_campaign_permission

        mock_frappe.session.user = "manager@test.com"
        mock_frappe.get_roles.return_value = ["SMS Manager"]
        mock_frappe.db.get_value.return_value = "Test Company"

        mock_doc = MagicMock()
        mock_doc.owner = "other@test.com"
        mock_doc.company = "Test Company"

        result = has_campaign_permission(mock_doc)

        assert result is True

    @patch("ovh_sms_integration.permissions.frappe")
    def test_sms_manager_no_company_campaign(self, mock_frappe: MagicMock) -> None:
        """SMS Manager a accès aux campagnes sans société."""
        from ovh_sms_integration.permissions import has_campaign_permission

        mock_frappe.session.user = "manager@test.com"
        mock_frappe.get_roles.return_value = ["SMS Manager"]
        mock_frappe.db.get_value.return_value = "Test Company"

        mock_doc = MagicMock()
        mock_doc.owner = "other@test.com"
        mock_doc.company = None

        result = has_campaign_permission(mock_doc)

        assert result is True

    @patch("ovh_sms_integration.permissions.frappe")
    def test_sms_user_own_campaign(self, mock_frappe: MagicMock) -> None:
        """SMS User a accès à ses propres campagnes."""
        from ovh_sms_integration.permissions import has_campaign_permission

        mock_frappe.session.user = "user@test.com"
        mock_frappe.get_roles.return_value = ["SMS User"]

        mock_doc = MagicMock()
        mock_doc.owner = "user@test.com"

        result = has_campaign_permission(mock_doc)

        assert result is True

    @patch("ovh_sms_integration.permissions.frappe")
    def test_sms_user_other_campaign(self, mock_frappe: MagicMock) -> None:
        """SMS User n'a pas accès aux campagnes des autres."""
        from ovh_sms_integration.permissions import has_campaign_permission

        mock_frappe.session.user = "user@test.com"
        mock_frappe.get_roles.return_value = ["SMS User"]

        mock_doc = MagicMock()
        mock_doc.owner = "other@test.com"

        result = has_campaign_permission(mock_doc)

        assert result is False

    @patch("ovh_sms_integration.permissions.frappe")
    def test_no_role_no_permission(self, mock_frappe: MagicMock) -> None:
        """Sans rôle SMS, pas d'accès."""
        from ovh_sms_integration.permissions import has_campaign_permission

        mock_frappe.session.user = "guest@test.com"
        mock_frappe.get_roles.return_value = ["Guest"]

        mock_doc = MagicMock()
        mock_doc.owner = "guest@test.com"

        result = has_campaign_permission(mock_doc)

        assert result is False


class TestValidateSmsPermissions:
    """Tests pour validate_sms_permissions."""

    @patch("ovh_sms_integration.permissions.frappe")
    @patch("ovh_sms_integration.permissions.has_campaign_permission")
    def test_permission_granted(
        self, mock_has_perm: MagicMock, mock_frappe: MagicMock
    ) -> None:
        """Test avec permission accordée."""
        from ovh_sms_integration.permissions import validate_sms_permissions

        mock_frappe.flags.in_install = False
        mock_frappe.flags.in_migrate = False
        mock_has_perm.return_value = True

        mock_doc = MagicMock()

        # Should not raise
        validate_sms_permissions(mock_doc, "before_save")

    @patch("ovh_sms_integration.permissions.frappe")
    @patch("ovh_sms_integration.permissions.has_campaign_permission")
    def test_permission_denied(
        self, mock_has_perm: MagicMock, mock_frappe: MagicMock
    ) -> None:
        """Test avec permission refusée."""
        from ovh_sms_integration.permissions import validate_sms_permissions

        mock_frappe.flags.in_install = False
        mock_frappe.flags.in_migrate = False
        mock_frappe._ = lambda x: x
        mock_frappe.throw = MagicMock(side_effect=Exception("Permission denied"))
        mock_has_perm.return_value = False

        mock_doc = MagicMock()

        with pytest.raises(Exception):
            validate_sms_permissions(mock_doc, "before_save")

    @patch("ovh_sms_integration.permissions.frappe")
    def test_skip_during_install(self, mock_frappe: MagicMock) -> None:
        """Test ignoré pendant l'installation."""
        from ovh_sms_integration.permissions import validate_sms_permissions

        mock_frappe.flags.in_install = True
        mock_frappe.flags.in_migrate = False

        mock_doc = MagicMock()

        # Should not raise even without permission
        validate_sms_permissions(mock_doc, "before_save")


class TestCheckUserSmsQuota:
    """Tests pour check_user_sms_quota."""

    @patch("ovh_sms_integration.permissions.frappe")
    def test_system_manager_quota(self, mock_frappe: MagicMock) -> None:
        """Test quota System Manager."""
        from ovh_sms_integration.permissions import check_user_sms_quota

        mock_frappe.get_roles.return_value = ["System Manager"]
        mock_frappe.db.exists.return_value = False  # SMS Campaign Log n'existe pas

        result = check_user_sms_quota("admin@test.com")

        assert result == 9999

    @patch("ovh_sms_integration.permissions.frappe")
    def test_sms_manager_quota(self, mock_frappe: MagicMock) -> None:
        """Test quota SMS Manager."""
        from ovh_sms_integration.permissions import check_user_sms_quota

        mock_frappe.get_roles.return_value = ["SMS Manager"]
        mock_frappe.db.exists.return_value = False

        result = check_user_sms_quota("manager@test.com")

        assert result == 500

    @patch("ovh_sms_integration.permissions.frappe")
    def test_sms_user_quota(self, mock_frappe: MagicMock) -> None:
        """Test quota SMS User."""
        from ovh_sms_integration.permissions import check_user_sms_quota

        mock_frappe.get_roles.return_value = ["SMS User"]
        mock_frappe.db.exists.return_value = False

        result = check_user_sms_quota("user@test.com")

        assert result == 100

    @patch("ovh_sms_integration.permissions.frappe")
    def test_no_quota_role(self, mock_frappe: MagicMock) -> None:
        """Test sans rôle avec quota."""
        from ovh_sms_integration.permissions import check_user_sms_quota

        mock_frappe.get_roles.return_value = ["Guest"]
        mock_frappe._ = lambda x: x
        mock_frappe.throw = MagicMock(side_effect=Exception("No quota"))

        with pytest.raises(Exception):
            check_user_sms_quota("guest@test.com")

    @patch("ovh_sms_integration.permissions.frappe")
    def test_quota_with_campaign_log(self, mock_frappe: MagicMock) -> None:
        """Test quota avec SMS Campaign Log existant."""
        from ovh_sms_integration.permissions import check_user_sms_quota

        mock_frappe.get_roles.return_value = ["SMS User"]
        mock_frappe.db.exists.return_value = True
        mock_frappe.db.count.return_value = 50  # 50 SMS envoyés

        result = check_user_sms_quota("user@test.com")

        assert result == 50  # 100 - 50

    @patch("ovh_sms_integration.permissions.frappe")
    def test_quota_exceeded(self, mock_frappe: MagicMock) -> None:
        """Test quota dépassé."""
        from ovh_sms_integration.permissions import check_user_sms_quota

        mock_frappe.get_roles.return_value = ["SMS User"]
        mock_frappe.db.exists.return_value = True
        mock_frappe.db.count.return_value = 100  # Quota atteint
        mock_frappe._ = lambda x: x
        mock_frappe.throw = MagicMock(side_effect=Exception("Quota exceeded"))

        with pytest.raises(Exception):
            check_user_sms_quota("user@test.com")


class TestGetUserSmsQuota:
    """Tests pour get_user_sms_quota (API endpoint)."""

    @patch("ovh_sms_integration.permissions.frappe")
    @patch("ovh_sms_integration.permissions.check_user_sms_quota")
    def test_get_quota_success(
        self, mock_check: MagicMock, mock_frappe: MagicMock
    ) -> None:
        """Test récupération quota avec succès."""
        from ovh_sms_integration.permissions import get_user_sms_quota

        mock_frappe.session.user = "user@test.com"
        mock_check.return_value = 75

        result = get_user_sms_quota()

        assert result["success"] is True
        assert result["remaining_quota"] == 75

    @patch("ovh_sms_integration.permissions.frappe")
    @patch("ovh_sms_integration.permissions.check_user_sms_quota")
    def test_get_quota_error(
        self, mock_check: MagicMock, mock_frappe: MagicMock
    ) -> None:
        """Test récupération quota avec erreur."""
        from ovh_sms_integration.permissions import get_user_sms_quota

        mock_frappe.session.user = "user@test.com"
        mock_check.side_effect = Exception("Quota error")

        result = get_user_sms_quota()

        assert result["success"] is False
        assert "Quota error" in result["message"]


class TestValidatePhoneConsent:
    """Tests pour validate_phone_consent."""

    @patch("ovh_sms_integration.permissions.frappe")
    def test_consent_valid_no_customer(self, mock_frappe: MagicMock) -> None:
        """Test consentement valide sans client trouvé."""
        from ovh_sms_integration.permissions import validate_phone_consent

        mock_frappe._ = lambda x: x
        mock_frappe.get_all.return_value = []
        mock_frappe.db.exists.return_value = False

        result = validate_phone_consent("+33612345678")

        assert result["success"] is True

    @patch("ovh_sms_integration.permissions.frappe")
    def test_consent_customer_opted_out(self, mock_frappe: MagicMock) -> None:
        """Test client ayant refusé les SMS."""
        from ovh_sms_integration.permissions import validate_phone_consent

        mock_frappe._ = lambda x: x
        mock_frappe.get_all.return_value = [{"name": "CUST-001", "sms_opt_out": True}]

        result = validate_phone_consent("+33612345678")

        assert result["success"] is False
        assert "refusé" in result["message"]

    @patch("ovh_sms_integration.permissions.frappe")
    def test_consent_phone_blacklisted(self, mock_frappe: MagicMock) -> None:
        """Test numéro sur liste noire."""
        from ovh_sms_integration.permissions import validate_phone_consent

        mock_frappe._ = lambda x: x
        mock_frappe.get_all.return_value = []
        mock_frappe.db.exists.return_value = True  # Blacklisted

        result = validate_phone_consent("+33612345678")

        assert result["success"] is False
        assert "blocage" in result["message"]

    @patch("ovh_sms_integration.permissions.frappe")
    def test_consent_error(self, mock_frappe: MagicMock) -> None:
        """Test erreur validation."""
        from ovh_sms_integration.permissions import validate_phone_consent

        mock_frappe._ = lambda x: x
        mock_frappe.get_all.side_effect = Exception("DB error")
        mock_frappe.log_error = MagicMock()

        result = validate_phone_consent("+33612345678")

        assert result["success"] is False


class TestCampaignLimits:
    """Tests pour validate_campaign_limits."""

    @patch("ovh_sms_integration.permissions.frappe")
    def test_limits_within_bounds(self, mock_frappe: MagicMock) -> None:
        """Test limites respectées."""
        from ovh_sms_integration.permissions import validate_campaign_limits

        mock_frappe.flags.in_install = False
        mock_frappe.flags.in_migrate = False
        mock_frappe.db.get_single_value.return_value = 10000

        mock_doc = MagicMock()
        mock_doc.total_customers = 100
        mock_doc.estimated_revenue = 1000

        # Should not raise
        validate_campaign_limits(mock_doc, "validate")

    @patch("ovh_sms_integration.permissions.frappe")
    def test_limits_sms_exceeded(self, mock_frappe: MagicMock) -> None:
        """Test limite SMS dépassée."""
        from ovh_sms_integration.permissions import validate_campaign_limits

        mock_frappe.flags.in_install = False
        mock_frappe.flags.in_migrate = False
        mock_frappe._ = lambda x: x
        mock_frappe.db.get_single_value.return_value = 100
        mock_frappe.throw = MagicMock(side_effect=Exception("Limit exceeded"))

        mock_doc = MagicMock()
        mock_doc.total_customers = 200  # Exceeds 100

        with pytest.raises(Exception):
            validate_campaign_limits(mock_doc, "validate")

    @patch("ovh_sms_integration.permissions.frappe")
    def test_limits_requires_approval(self, mock_frappe: MagicMock) -> None:
        """Test campagne nécessitant approbation."""
        from ovh_sms_integration.permissions import validate_campaign_limits

        mock_frappe.flags.in_install = False
        mock_frappe.flags.in_migrate = False
        mock_frappe.db.get_single_value.side_effect = [10000, 5000, 1000]

        mock_doc = MagicMock()
        mock_doc.total_customers = 5000  # > 1000, needs approval
        mock_doc.estimated_revenue = 10000  # > 5000, needs approval
        mock_doc.requires_approval = 0

        validate_campaign_limits(mock_doc, "validate")

        assert mock_doc.requires_approval == 1


class TestConcurrentCampaigns:
    """Tests pour check_concurrent_campaigns."""

    @patch("ovh_sms_integration.permissions.frappe")
    def test_concurrent_ok(self, mock_frappe: MagicMock) -> None:
        """Test avec campagnes sous la limite."""
        from ovh_sms_integration.permissions import check_concurrent_campaigns

        mock_frappe.session.user = "user@test.com"
        mock_frappe.db.get_single_value.return_value = 3
        mock_frappe.db.count.return_value = 1  # 1 campagne active

        # Should not raise
        check_concurrent_campaigns()

    @patch("ovh_sms_integration.permissions.frappe")
    def test_concurrent_exceeded(self, mock_frappe: MagicMock) -> None:
        """Test limite de campagnes atteinte."""
        from ovh_sms_integration.permissions import check_concurrent_campaigns

        mock_frappe.session.user = "user@test.com"
        mock_frappe._ = lambda x: x
        mock_frappe.db.get_single_value.return_value = 3
        mock_frappe.db.count.return_value = 3  # 3 campagnes actives = limite
        mock_frappe.throw = MagicMock(side_effect=Exception("Limit reached"))

        with pytest.raises(Exception):
            check_concurrent_campaigns()


class TestSecuritySetup:
    """Tests pour les fonctions de configuration sécurité."""

    @patch("ovh_sms_integration.permissions.frappe")
    @patch("ovh_sms_integration.permissions.create_sms_roles")
    @patch("ovh_sms_integration.permissions.setup_default_permissions")
    @patch("ovh_sms_integration.permissions.setup_security_limits")
    def test_setup_campaign_security(
        self,
        mock_limits: MagicMock,
        mock_perms: MagicMock,
        mock_roles: MagicMock,
        mock_frappe: MagicMock,
    ) -> None:
        """Test configuration sécurité complète."""
        from ovh_sms_integration.permissions import setup_campaign_security

        setup_campaign_security()

        mock_roles.assert_called_once()
        mock_perms.assert_called_once()
        mock_limits.assert_called_once()

    @patch("ovh_sms_integration.permissions.frappe")
    def test_create_sms_roles_new(self, mock_frappe: MagicMock) -> None:
        """Test création de rôles."""
        from ovh_sms_integration.permissions import create_sms_roles

        mock_frappe.db.exists.return_value = False
        mock_frappe.get_doc.return_value = MagicMock()
        mock_frappe.logger.return_value = MagicMock()

        create_sms_roles()

        # Should create 3 roles
        assert mock_frappe.get_doc.call_count == 3

    @patch("ovh_sms_integration.permissions.frappe")
    def test_create_sms_roles_existing(self, mock_frappe: MagicMock) -> None:
        """Test avec rôles existants."""
        from ovh_sms_integration.permissions import create_sms_roles

        mock_frappe.db.exists.return_value = True  # Roles exist

        create_sms_roles()

        # Should not create any roles
        mock_frappe.get_doc.assert_not_called()


class TestGdprCompliance:
    """Tests pour la conformité RGPD."""

    @patch("ovh_sms_integration.permissions.frappe")
    @patch("ovh_sms_integration.permissions.anonymize_campaign_data")
    def test_enforce_gdpr_compliance(
        self, mock_anonymize: MagicMock, mock_frappe: MagicMock
    ) -> None:
        """Test application conformité RGPD."""
        from ovh_sms_integration.permissions import enforce_gdpr_compliance

        mock_frappe.db.get_single_value.return_value = 1095
        mock_frappe.utils.add_days.return_value = "2020-01-01"
        mock_frappe.utils.today.return_value = "2023-01-01"
        mock_frappe.get_all.return_value = ["CAMP-001", "CAMP-002"]

        enforce_gdpr_compliance()

        assert mock_anonymize.call_count == 2

    @patch("ovh_sms_integration.permissions.frappe")
    def test_anonymize_campaign_data(self, mock_frappe: MagicMock) -> None:
        """Test anonymisation des données."""
        from ovh_sms_integration.permissions import anonymize_campaign_data

        mock_item = MagicMock()
        mock_item.customer_mobile = "+33612345678"
        mock_item.customer_name = "Jean Dupont"

        mock_doc = MagicMock()
        mock_doc.pricing_items = [mock_item]
        mock_frappe.get_doc.return_value = mock_doc
        mock_frappe.logger.return_value = MagicMock()

        anonymize_campaign_data("CAMP-001")

        assert mock_item.customer_mobile == "***ANONYMIZED***"
        assert mock_item.customer_name == "Client Anonyme"
        assert mock_doc.anonymized == 1
        mock_doc.save.assert_called_once()


class TestDecorators:
    """Tests pour les décorateurs de sécurité."""

    @patch("ovh_sms_integration.permissions.validate_sms_sending_permission")
    def test_require_sms_permission_granted(self, mock_validate: MagicMock) -> None:
        """Test décorateur avec permission accordée."""
        from ovh_sms_integration.permissions import require_sms_permission

        @require_sms_permission
        def test_function() -> str:
            return "success"

        result = test_function()

        assert result == "success"
        mock_validate.assert_called_once()

    @patch("ovh_sms_integration.permissions.validate_sms_sending_permission")
    def test_require_sms_permission_denied(self, mock_validate: MagicMock) -> None:
        """Test décorateur avec permission refusée."""
        from ovh_sms_integration.permissions import require_sms_permission

        mock_validate.side_effect = Exception("Permission denied")

        @require_sms_permission
        def test_function() -> str:
            return "success"

        with pytest.raises(Exception):
            test_function()

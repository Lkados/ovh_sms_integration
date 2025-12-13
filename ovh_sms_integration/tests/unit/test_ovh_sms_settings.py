# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module ovh_sms_settings.py.

Ce module teste les fonctions de configuration et d'envoi de SMS OVH.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestOVHSMSSettingsValidate:
    """Tests pour la méthode validate du DocType."""

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings.frappe"
    )
    def test_validate_enabled_missing_app_key(self, mock_frappe: MagicMock) -> None:
        """Test validation sans application_key."""
        from ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings import (
            OVHSMSSettings,
        )

        mock_frappe.throw.side_effect = Exception("Application Key est requis")

        settings = MagicMock(spec=OVHSMSSettings)
        settings.enabled = True
        settings.application_key = None

        OVHSMSSettings.validate(settings)

        mock_frappe.throw.assert_called()

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings.frappe"
    )
    def test_validate_disabled(self, mock_frappe: MagicMock) -> None:
        """Test validation avec intégration désactivée."""
        from ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings import (
            OVHSMSSettings,
        )

        settings = MagicMock(spec=OVHSMSSettings)
        settings.enabled = False

        OVHSMSSettings.validate(settings)

        mock_frappe.throw.assert_not_called()

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings.frappe"
    )
    def test_validate_enabled_complete(self, mock_frappe: MagicMock) -> None:
        """Test validation avec configuration complète."""
        from ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings import (
            OVHSMSSettings,
        )

        settings = MagicMock(spec=OVHSMSSettings)
        settings.enabled = True
        settings.application_key = "test_key"
        settings.get_password.return_value = "secret"
        settings.auto_detect_service = True

        OVHSMSSettings.validate(settings)

        mock_frappe.throw.assert_not_called()


class TestGetServiceName:
    """Tests pour la méthode get_service_name."""

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings.frappe"
    )
    def test_get_service_name_manual(self, mock_frappe: MagicMock) -> None:
        """Test récupération nom service manuel."""
        from ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings import (
            OVHSMSSettings,
        )

        settings = MagicMock(spec=OVHSMSSettings)
        settings.auto_detect_service = False
        settings.service_name = "sms-test-123"

        result = OVHSMSSettings.get_service_name(settings)

        assert result == "sms-test-123"

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings.frappe"
    )
    def test_get_service_name_auto_detect(self, mock_frappe: MagicMock) -> None:
        """Test auto-détection du service."""
        from ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings import (
            OVHSMSSettings,
        )

        settings = MagicMock(spec=OVHSMSSettings)
        settings.auto_detect_service = True
        settings.service_name = None
        settings.get_sms_services.return_value = ["sms-auto-001", "sms-auto-002"]

        result = OVHSMSSettings.get_service_name(settings)

        assert result == "sms-auto-001"

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings.frappe"
    )
    def test_get_service_name_no_services(self, mock_frappe: MagicMock) -> None:
        """Test auto-détection sans services."""
        from ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings import (
            OVHSMSSettings,
        )

        mock_frappe.throw.side_effect = Exception("Aucun service SMS trouvé")

        settings = MagicMock(spec=OVHSMSSettings)
        settings.auto_detect_service = True
        settings.service_name = None
        settings.get_sms_services.return_value = []

        with pytest.raises(Exception):
            OVHSMSSettings.get_service_name(settings)


class TestCreateSignature:
    """Tests pour la méthode _create_signature."""

    def test_create_signature_format(self) -> None:
        """Test format de signature."""
        from ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings import (
            OVHSMSSettings,
        )

        settings = MagicMock(spec=OVHSMSSettings)
        settings.get_password.side_effect = lambda key: {
            "application_secret": "secret123",
            "consumer_key": "consumer456",
        }.get(key)
        settings.application_secret = "secret123"
        settings.consumer_key = "consumer456"

        result = OVHSMSSettings._create_signature(
            settings, "GET", "https://eu.api.ovh.com/1.0/sms", ""
        )

        assert "signature" in result
        assert "timestamp" in result
        assert result["signature"].startswith("$1$")
        assert len(result["signature"]) > 10

    def test_create_signature_with_body(self) -> None:
        """Test signature avec corps de requête."""
        from ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings import (
            OVHSMSSettings,
        )

        settings = MagicMock(spec=OVHSMSSettings)
        settings.get_password.side_effect = lambda key: {
            "application_secret": "secret123",
            "consumer_key": "consumer456",
        }.get(key)
        settings.application_secret = "secret123"
        settings.consumer_key = "consumer456"

        body = '{"message":"Hello","receivers":["+33612345678"]}'
        result = OVHSMSSettings._create_signature(
            settings, "POST", "https://eu.api.ovh.com/1.0/sms/service/jobs", body
        )

        assert result["signature"].startswith("$1$")


class TestSendSMS:
    """Tests pour la méthode send_sms."""

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings.requests"
    )
    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings.frappe"
    )
    def test_send_sms_success(
        self, mock_frappe: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test envoi SMS réussi."""
        from ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings import (
            OVHSMSSettings,
        )

        mock_frappe._ = lambda x: x
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ids": [12345],
            "validReceivers": ["+33612345678"],
        }
        mock_response.raise_for_status.return_value = None
        mock_requests.post.return_value = mock_response

        settings = MagicMock(spec=OVHSMSSettings)
        settings.get_service_name.return_value = "sms-test-001"
        settings.get_best_sender.return_value = "ERPNext"
        settings.application_key = "test_key"
        settings.get_password.return_value = "consumer_key"
        settings._create_signature.return_value = {
            "signature": "$1$abc",
            "timestamp": "123",
        }

        result = OVHSMSSettings.send_sms(
            settings, "Hello test", "+33612345678", "ERPNext"
        )

        assert result["success"] is True
        assert "sender_used" in result

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings.requests"
    )
    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings.frappe"
    )
    def test_send_sms_api_error(
        self, mock_frappe: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test envoi SMS avec erreur API."""
        import requests as real_requests
        from ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings import (
            OVHSMSSettings,
        )

        mock_requests.exceptions = real_requests.exceptions
        mock_requests.post.side_effect = real_requests.exceptions.RequestException(
            "API Error"
        )

        settings = MagicMock(spec=OVHSMSSettings)
        settings.get_service_name.return_value = "sms-test-001"
        settings.get_best_sender.return_value = "ERPNext"
        settings.application_key = "test_key"
        settings.get_password.return_value = "consumer_key"
        settings._create_signature.return_value = {
            "signature": "$1$abc",
            "timestamp": "123",
        }

        result = OVHSMSSettings.send_sms(settings, "Hello test", "+33612345678")

        assert result["success"] is False
        assert "Erreur" in result["message"]


class TestTestConnection:
    """Tests pour la méthode test_connection."""

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings.requests"
    )
    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings.frappe"
    )
    def test_connection_success(
        self, mock_frappe: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test connexion réussie."""
        from ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings import (
            OVHSMSSettings,
        )

        mock_frappe._ = lambda x: x
        mock_response = MagicMock()
        mock_response.json.return_value = {"nichandle": "ab12345-ovh"}
        mock_response.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_response

        settings = MagicMock(spec=OVHSMSSettings)
        settings.application_key = "test_key"
        settings.get_password.return_value = "consumer_key"
        settings._create_signature.return_value = {
            "signature": "$1$abc",
            "timestamp": "123",
        }
        settings.get_sms_services.return_value = ["sms-test-001"]
        settings.get_service_name.return_value = "sms-test-001"
        settings.get_service_details.return_value = {"creditsLeft": 100}
        settings.get_available_senders.return_value = ["ERPNext", "MyApp"]

        result = OVHSMSSettings.test_connection(settings)

        assert result["success"] is True
        assert "ab12345-ovh" in result["message"]

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings.requests"
    )
    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings.frappe"
    )
    def test_connection_no_services(
        self, mock_frappe: MagicMock, mock_requests: MagicMock
    ) -> None:
        """Test connexion sans services SMS."""
        from ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings import (
            OVHSMSSettings,
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {"nichandle": "ab12345-ovh"}
        mock_response.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_response

        settings = MagicMock(spec=OVHSMSSettings)
        settings.application_key = "test_key"
        settings.get_password.return_value = "consumer_key"
        settings._create_signature.return_value = {
            "signature": "$1$abc",
            "timestamp": "123",
        }
        settings.get_sms_services.return_value = []

        result = OVHSMSSettings.test_connection(settings)

        assert result["success"] is False
        assert "aucun service" in result["message"].lower()


class TestTestOVHConnection:
    """Tests pour la fonction test_ovh_connection."""

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings.frappe"
    )
    def test_connection_disabled(self, mock_frappe: MagicMock) -> None:
        """Test connexion avec intégration désactivée."""
        from ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings import (
            test_ovh_connection,
        )

        mock_settings = MagicMock()
        mock_settings.enabled = False
        mock_frappe.get_single.return_value = mock_settings

        result = test_ovh_connection()

        assert result["success"] is False
        assert "pas activée" in result["message"]

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings.frappe"
    )
    def test_connection_enabled(self, mock_frappe: MagicMock) -> None:
        """Test connexion avec intégration activée."""
        from ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings import (
            test_ovh_connection,
        )

        mock_settings = MagicMock()
        mock_settings.enabled = True
        mock_settings.test_connection.return_value = {"success": True, "message": "OK"}
        mock_frappe.get_single.return_value = mock_settings

        result = test_ovh_connection()

        assert result["success"] is True


class TestSendTestSMS:
    """Tests pour la fonction send_test_sms."""

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings.frappe"
    )
    def test_send_test_no_phone(self, mock_frappe: MagicMock) -> None:
        """Test envoi sans numéro de téléphone."""
        from ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings import (
            send_test_sms,
        )

        result = send_test_sms(phone_number=None)

        assert result["success"] is False
        assert "requis" in result["message"]

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings.frappe"
    )
    def test_send_test_disabled(self, mock_frappe: MagicMock) -> None:
        """Test envoi avec intégration désactivée."""
        from ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings import (
            send_test_sms,
        )

        mock_settings = MagicMock()
        mock_settings.enabled = False
        mock_frappe.get_single.return_value = mock_settings

        result = send_test_sms(phone_number="+33612345678")

        assert result["success"] is False
        assert "pas activée" in result["message"]

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings.frappe"
    )
    def test_send_test_success(self, mock_frappe: MagicMock) -> None:
        """Test envoi réussi."""
        from ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings import (
            send_test_sms,
        )

        mock_settings = MagicMock()
        mock_settings.enabled = True
        mock_settings.send_sms.return_value = {"success": True, "message": "SMS envoyé"}
        mock_frappe.get_single.return_value = mock_settings

        result = send_test_sms(phone_number="+33612345678", message="Test")

        assert result["success"] is True


class TestGetAccountBalance:
    """Tests pour la fonction get_account_balance."""

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings.frappe"
    )
    def test_balance_disabled(self, mock_frappe: MagicMock) -> None:
        """Test solde avec intégration désactivée."""
        from ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings import (
            get_account_balance,
        )

        mock_settings = MagicMock()
        mock_settings.enabled = False
        mock_frappe.get_single.return_value = mock_settings

        result = get_account_balance()

        assert result["success"] is False


class TestCreateSender:
    """Tests pour la méthode create_sender."""

    def test_sender_name_validation_alphanumeric(self) -> None:
        """Test validation nom expéditeur - caractères alphanumériques."""
        import re

        # Noms valides
        valid_names = ["ERPNext", "MyApp123", "A", "12345678901"]
        for name in valid_names:
            assert re.match(r"^[a-zA-Z0-9]{1,11}$", name), f"{name} devrait être valide"

        # Noms invalides
        invalid_names = ["ERPNext!", "My App", "trop_long_nom_12", "émojis😀"]
        for name in invalid_names:
            assert not re.match(
                r"^[a-zA-Z0-9]{1,11}$", name
            ), f"{name} devrait être invalide"


class TestGetBestSender:
    """Tests pour la méthode get_best_sender."""

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings.frappe"
    )
    def test_best_sender_default_exists(self, mock_frappe: MagicMock) -> None:
        """Test avec expéditeur par défaut existant."""
        from ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings import (
            OVHSMSSettings,
        )

        settings = MagicMock(spec=OVHSMSSettings)
        settings.default_sender = "MyCompany"
        settings.validate_and_create_sender.return_value = {"success": True}

        result = OVHSMSSettings.get_best_sender(settings)

        assert result == "MyCompany"

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings.frappe"
    )
    def test_best_sender_from_available(self, mock_frappe: MagicMock) -> None:
        """Test avec expéditeur disponible."""
        from ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings import (
            OVHSMSSettings,
        )

        settings = MagicMock(spec=OVHSMSSettings)
        settings.default_sender = None
        settings.get_available_senders.return_value = ["FirstSender", "SecondSender"]

        result = OVHSMSSettings.get_best_sender(settings)

        assert result == "FirstSender"


class TestValidateAndCreateSender:
    """Tests pour la méthode validate_and_create_sender."""

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings.frappe"
    )
    def test_sender_already_exists(self, mock_frappe: MagicMock) -> None:
        """Test avec expéditeur existant."""
        from ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings import (
            OVHSMSSettings,
        )

        mock_frappe._ = lambda x: x

        settings = MagicMock(spec=OVHSMSSettings)
        settings.get_available_senders.return_value = ["ERPNext", "MyApp"]

        result = OVHSMSSettings.validate_and_create_sender(settings, "ERPNext")

        assert result["success"] is True
        assert result["created"] is False

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings.frappe"
    )
    def test_sender_needs_creation(self, mock_frappe: MagicMock) -> None:
        """Test création nouvel expéditeur."""
        from ovh_sms_integration.ovh_sms_integration.doctype.ovh_sms_settings.ovh_sms_settings import (
            OVHSMSSettings,
        )

        mock_frappe._ = lambda x: x

        settings = MagicMock(spec=OVHSMSSettings)
        settings.get_available_senders.return_value = ["OtherSender"]
        settings.create_sender.return_value = {"success": True, "message": "Créé"}

        result = OVHSMSSettings.validate_and_create_sender(settings, "NewSender")

        assert result["success"] is True
        assert result["created"] is True

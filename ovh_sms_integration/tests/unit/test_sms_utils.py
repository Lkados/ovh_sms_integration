# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module utils/sms_utils.py.

Ce module teste les utilitaires SMS: envoi, validation, formatage.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


class TestValidatePhoneNumber:
    """Tests pour la fonction validate_phone_number."""

    @patch("ovh_sms_integration.utils.sms_utils.frappe")
    def test_french_local_format(self, mock_frappe: MagicMock) -> None:
        """Test format français local."""
        from ovh_sms_integration.utils.sms_utils import validate_phone_number

        mock_frappe._ = lambda x: x

        result = validate_phone_number("0612345678")
        assert result == "+33612345678"

    @patch("ovh_sms_integration.utils.sms_utils.frappe")
    def test_international_format(self, mock_frappe: MagicMock) -> None:
        """Test format international."""
        from ovh_sms_integration.utils.sms_utils import validate_phone_number

        mock_frappe._ = lambda x: x

        result = validate_phone_number("+33612345678")
        assert result == "+33612345678"

    @patch("ovh_sms_integration.utils.sms_utils.frappe")
    def test_with_spaces(self, mock_frappe: MagicMock) -> None:
        """Test avec espaces."""
        from ovh_sms_integration.utils.sms_utils import validate_phone_number

        mock_frappe._ = lambda x: x

        result = validate_phone_number("06 12 34 56 78")
        assert result == "+33612345678"

    @patch("ovh_sms_integration.utils.sms_utils.frappe")
    def test_with_dashes(self, mock_frappe: MagicMock) -> None:
        """Test avec tirets."""
        from ovh_sms_integration.utils.sms_utils import validate_phone_number

        mock_frappe._ = lambda x: x

        result = validate_phone_number("06-12-34-56-78")
        assert result == "+33612345678"

    @patch("ovh_sms_integration.utils.sms_utils.frappe")
    def test_without_prefix(self, mock_frappe: MagicMock) -> None:
        """Test sans préfixe."""
        from ovh_sms_integration.utils.sms_utils import validate_phone_number

        mock_frappe._ = lambda x: x

        result = validate_phone_number("612345678")
        assert result == "+33612345678"

    @patch("ovh_sms_integration.utils.sms_utils.frappe")
    def test_empty_phone(self, mock_frappe: MagicMock) -> None:
        """Test avec numéro vide."""
        from ovh_sms_integration.utils.sms_utils import validate_phone_number

        mock_frappe._ = lambda x: x

        with pytest.raises(ValueError):
            validate_phone_number("")

    @patch("ovh_sms_integration.utils.sms_utils.frappe")
    def test_none_phone(self, mock_frappe: MagicMock) -> None:
        """Test avec numéro None."""
        from ovh_sms_integration.utils.sms_utils import validate_phone_number

        mock_frappe._ = lambda x: x

        with pytest.raises(ValueError):
            validate_phone_number(None)

    @patch("ovh_sms_integration.utils.sms_utils.frappe")
    def test_invalid_phone(self, mock_frappe: MagicMock) -> None:
        """Test avec numéro invalide."""
        from ovh_sms_integration.utils.sms_utils import validate_phone_number

        mock_frappe._ = lambda x: x

        with pytest.raises(ValueError):
            validate_phone_number("invalid")

    @patch("ovh_sms_integration.utils.sms_utils.frappe")
    def test_too_short(self, mock_frappe: MagicMock) -> None:
        """Test numéro trop court."""
        from ovh_sms_integration.utils.sms_utils import validate_phone_number

        mock_frappe._ = lambda x: x

        with pytest.raises(ValueError):
            validate_phone_number("0612")


class TestFormatMessageTemplate:
    """Tests pour la fonction format_message_template."""

    @patch("ovh_sms_integration.utils.sms_utils.frappe")
    def test_simple_template(self, mock_frappe: MagicMock) -> None:
        """Test template simple."""
        from ovh_sms_integration.utils.sms_utils import format_message_template

        mock_frappe._ = lambda x: x

        result = format_message_template("Bonjour {{name}}", {"name": "Jean"})
        assert result == "Bonjour Jean"

    @patch("ovh_sms_integration.utils.sms_utils.frappe")
    def test_multiple_variables(self, mock_frappe: MagicMock) -> None:
        """Test avec plusieurs variables."""
        from ovh_sms_integration.utils.sms_utils import format_message_template

        mock_frappe._ = lambda x: x

        result = format_message_template(
            "{{greeting}} {{name}}, montant: {{amount}}€",
            {"greeting": "Bonjour", "name": "Marie", "amount": 150.50},
        )
        assert "Bonjour" in result
        assert "Marie" in result
        assert "150.5" in result

    @patch("ovh_sms_integration.utils.sms_utils.frappe")
    def test_with_datetime(self, mock_frappe: MagicMock) -> None:
        """Test avec datetime."""
        from ovh_sms_integration.utils.sms_utils import format_message_template

        mock_frappe._ = lambda x: x

        dt = datetime(2025, 1, 15, 14, 30)
        result = format_message_template("RDV le {{date}}", {"date": dt})
        assert "15/01/2025" in result
        assert "14:30" in result

    @patch("ovh_sms_integration.utils.sms_utils.frappe")
    def test_empty_template(self, mock_frappe: MagicMock) -> None:
        """Test template vide."""
        from ovh_sms_integration.utils.sms_utils import format_message_template

        mock_frappe._ = lambda x: x

        result = format_message_template("", {"name": "Test"})
        assert result == ""

    @patch("ovh_sms_integration.utils.sms_utils.frappe")
    def test_empty_context(self, mock_frappe: MagicMock) -> None:
        """Test contexte vide."""
        from ovh_sms_integration.utils.sms_utils import format_message_template

        mock_frappe._ = lambda x: x

        result = format_message_template("Hello", {})
        assert result == "Hello"

    @patch("ovh_sms_integration.utils.sms_utils.frappe")
    def test_none_context(self, mock_frappe: MagicMock) -> None:
        """Test contexte None."""
        from ovh_sms_integration.utils.sms_utils import format_message_template

        mock_frappe._ = lambda x: x

        result = format_message_template("Hello", None)
        assert result == "Hello"

    @patch("ovh_sms_integration.utils.sms_utils.frappe")
    def test_object_conversion(self, mock_frappe: MagicMock) -> None:
        """Test conversion objet en string."""
        from ovh_sms_integration.utils.sms_utils import format_message_template

        mock_frappe._ = lambda x: x

        class CustomObj:
            def __str__(self) -> str:
                return "CustomValue"

        result = format_message_template("Value: {{obj}}", {"obj": CustomObj()})
        assert "CustomValue" in result


class TestGetOvhSmsSettings:
    """Tests pour la fonction get_ovh_sms_settings."""

    @patch("ovh_sms_integration.utils.sms_utils.frappe")
    def test_settings_enabled(self, mock_frappe: MagicMock) -> None:
        """Test avec paramètres activés."""
        from ovh_sms_integration.utils.sms_utils import get_ovh_sms_settings

        mock_settings = MagicMock()
        mock_settings.enabled = True
        mock_frappe.get_single.return_value = mock_settings

        result = get_ovh_sms_settings()

        assert result == mock_settings

    @patch("ovh_sms_integration.utils.sms_utils.frappe")
    def test_settings_disabled(self, mock_frappe: MagicMock) -> None:
        """Test avec paramètres désactivés."""
        from ovh_sms_integration.utils.sms_utils import get_ovh_sms_settings

        mock_settings = MagicMock()
        mock_settings.enabled = False
        mock_frappe.get_single.return_value = mock_settings

        result = get_ovh_sms_settings()

        assert result is None


class TestSendSms:
    """Tests pour la fonction send_sms."""

    @patch("ovh_sms_integration.utils.sms_utils.get_ovh_sms_settings")
    @patch("ovh_sms_integration.utils.sms_utils.validate_phone_number")
    @patch("ovh_sms_integration.utils.sms_utils.frappe")
    def test_send_sms_success(
        self,
        mock_frappe: MagicMock,
        mock_validate: MagicMock,
        mock_get_settings: MagicMock,
    ) -> None:
        """Test envoi SMS avec succès."""
        from ovh_sms_integration.utils.sms_utils import send_sms

        mock_frappe._ = lambda x: x
        mock_validate.return_value = "+33612345678"

        mock_settings = MagicMock()
        mock_settings.send_sms.return_value = {"success": True}
        mock_get_settings.return_value = mock_settings

        result = send_sms("Test message", "0612345678")

        assert result is not None
        assert result["success"] is True

    @patch("ovh_sms_integration.utils.sms_utils.get_ovh_sms_settings")
    @patch("ovh_sms_integration.utils.sms_utils.frappe")
    def test_send_sms_disabled(
        self, mock_frappe: MagicMock, mock_get_settings: MagicMock
    ) -> None:
        """Test envoi avec intégration désactivée."""
        from ovh_sms_integration.utils.sms_utils import send_sms

        mock_frappe._ = lambda x: x
        mock_get_settings.return_value = None

        result = send_sms("Test message", "0612345678")

        assert result is None
        mock_frappe.log_error.assert_called()

    @patch("ovh_sms_integration.utils.sms_utils.get_ovh_sms_settings")
    @patch("ovh_sms_integration.utils.sms_utils.validate_phone_number")
    @patch("ovh_sms_integration.utils.sms_utils.frappe")
    def test_send_sms_invalid_phone(
        self,
        mock_frappe: MagicMock,
        mock_validate: MagicMock,
        mock_get_settings: MagicMock,
    ) -> None:
        """Test envoi avec numéro invalide."""
        from ovh_sms_integration.utils.sms_utils import send_sms

        mock_frappe._ = lambda x: x
        mock_validate.side_effect = ValueError("Invalid phone")
        mock_get_settings.return_value = MagicMock()

        with pytest.raises(ValueError):
            send_sms("Test", "invalid")

    @patch("ovh_sms_integration.utils.sms_utils.get_ovh_sms_settings")
    @patch("ovh_sms_integration.utils.sms_utils.validate_phone_number")
    @patch("ovh_sms_integration.utils.sms_utils.format_message_template")
    @patch("ovh_sms_integration.utils.sms_utils.frappe")
    def test_send_sms_with_template(
        self,
        mock_frappe: MagicMock,
        mock_format: MagicMock,
        mock_validate: MagicMock,
        mock_get_settings: MagicMock,
    ) -> None:
        """Test envoi avec template."""
        from ovh_sms_integration.utils.sms_utils import send_sms

        mock_frappe._ = lambda x: x
        mock_validate.return_value = "+33612345678"
        mock_format.return_value = "Bonjour Jean"

        mock_settings = MagicMock()
        mock_settings.send_sms.return_value = {"success": True}
        mock_get_settings.return_value = mock_settings

        result = send_sms(
            "Bonjour {{name}}",
            "0612345678",
            context={"name": "Jean"},
        )

        mock_format.assert_called_once()
        assert result is not None


class TestGetContactMobile:
    """Tests pour la fonction get_contact_mobile."""

    @patch("ovh_sms_integration.utils.sms_utils.frappe")
    def test_mobile_no_field(self, mock_frappe: MagicMock) -> None:
        """Test avec champ mobile_no."""
        from ovh_sms_integration.utils.sms_utils import get_contact_mobile

        mock_doc = MagicMock()
        mock_doc.mobile_no = "+33612345678"
        mock_doc.get = MagicMock(side_effect=lambda x: getattr(mock_doc, x, None))

        result = get_contact_mobile(mock_doc)

        assert result == "+33612345678"

    @patch("ovh_sms_integration.utils.sms_utils.frappe")
    def test_phone_no_field(self, mock_frappe: MagicMock) -> None:
        """Test avec champ phone_no."""
        from ovh_sms_integration.utils.sms_utils import get_contact_mobile

        mock_doc = MagicMock()
        mock_doc.mobile_no = None
        mock_doc.phone_no = "+33612345678"

        def mock_get(field: str) -> Any:
            return getattr(mock_doc, field, None)

        mock_doc.get = mock_get

        result = get_contact_mobile(mock_doc)

        assert result == "+33612345678"

    @patch("ovh_sms_integration.utils.sms_utils.frappe")
    def test_no_mobile(self, mock_frappe: MagicMock) -> None:
        """Test sans numéro mobile."""
        from ovh_sms_integration.utils.sms_utils import get_contact_mobile

        mock_doc = MagicMock()
        mock_doc.mobile_no = None
        mock_doc.phone_no = None
        mock_doc.contact_mobile = None
        mock_doc.mobile = None
        mock_doc.phone = None
        mock_doc.contact_person = None
        mock_doc.get = MagicMock(return_value=None)

        result = get_contact_mobile(mock_doc)

        assert result is None


class TestPhoneValidationEdgeCases:
    """Tests de cas limites pour la validation de numéros."""

    @patch("ovh_sms_integration.utils.sms_utils.frappe")
    def test_international_with_spaces(self, mock_frappe: MagicMock) -> None:
        """Test format international avec espaces."""
        from ovh_sms_integration.utils.sms_utils import validate_phone_number

        mock_frappe._ = lambda x: x

        result = validate_phone_number("+33 6 12 34 56 78")
        assert result == "+33612345678"

    @patch("ovh_sms_integration.utils.sms_utils.frappe")
    def test_parentheses(self, mock_frappe: MagicMock) -> None:
        """Test avec parenthèses."""
        from ovh_sms_integration.utils.sms_utils import validate_phone_number

        mock_frappe._ = lambda x: x

        result = validate_phone_number("(06) 12 34 56 78")
        assert result == "+33612345678"

    @patch("ovh_sms_integration.utils.sms_utils.frappe")
    def test_dots(self, mock_frappe: MagicMock) -> None:
        """Test avec points."""
        from ovh_sms_integration.utils.sms_utils import validate_phone_number

        mock_frappe._ = lambda x: x

        result = validate_phone_number("06.12.34.56.78")
        assert result == "+33612345678"


class TestMessageTemplateEdgeCases:
    """Tests de cas limites pour les templates."""

    @patch("ovh_sms_integration.utils.sms_utils.frappe")
    def test_special_characters(self, mock_frappe: MagicMock) -> None:
        """Test caractères spéciaux."""
        from ovh_sms_integration.utils.sms_utils import format_message_template

        mock_frappe._ = lambda x: x

        result = format_message_template(
            "Prix: {{price}}€ / unité",
            {"price": "15.50"},
        )
        assert "15.50€" in result

    @patch("ovh_sms_integration.utils.sms_utils.frappe")
    def test_unicode(self, mock_frappe: MagicMock) -> None:
        """Test caractères unicode."""
        from ovh_sms_integration.utils.sms_utils import format_message_template

        mock_frappe._ = lambda x: x

        result = format_message_template(
            "Bonjour {{name}} 👋",
            {"name": "François"},
        )
        assert "François" in result

    @patch("ovh_sms_integration.utils.sms_utils.frappe")
    def test_integer_value(self, mock_frappe: MagicMock) -> None:
        """Test valeur entière."""
        from ovh_sms_integration.utils.sms_utils import format_message_template

        mock_frappe._ = lambda x: x

        result = format_message_template(
            "Quantité: {{qty}}",
            {"qty": 42},
        )
        assert "42" in result

    @patch("ovh_sms_integration.utils.sms_utils.frappe")
    def test_float_value(self, mock_frappe: MagicMock) -> None:
        """Test valeur flottante."""
        from ovh_sms_integration.utils.sms_utils import format_message_template

        mock_frappe._ = lambda x: x

        result = format_message_template(
            "Total: {{total}}",
            {"total": 123.45},
        )
        assert "123.45" in result

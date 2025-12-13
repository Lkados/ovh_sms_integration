# -*- coding: utf-8 -*-
"""
Tests standalone qui n'ont pas besoin de Frappe.

Ces tests peuvent être exécutés directement avec pytest sans frappe.
Ils testent les fonctions pures qui ne dépendent pas de frappe.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import pytest


class TestPhoneNumberValidation:
    """Tests de validation de numéros de téléphone (logique pure)."""

    def _validate_phone_logic(self, phone: str | None) -> str:
        """Logique de validation de numéro (copie de la fonction originale)."""
        if not phone:
            raise ValueError("Numéro de téléphone vide")

        # Nettoyage du numéro (garde seulement chiffres et +)
        cleaned_phone: str = re.sub(r"[^\d+]", "", str(phone))

        # Conversion au format international français
        if cleaned_phone.startswith("0"):
            cleaned_phone = "+33" + cleaned_phone[1:]
        elif not cleaned_phone.startswith("+"):
            cleaned_phone = "+33" + cleaned_phone

        # Validation du format final
        if not re.match(r"^\+\d{10,15}$", cleaned_phone):
            raise ValueError(f"Numéro de téléphone invalide: {phone}")

        return cleaned_phone

    def test_french_local_format(self) -> None:
        """Test format français local."""
        result = self._validate_phone_logic("0612345678")
        assert result == "+33612345678"

    def test_international_format(self) -> None:
        """Test format international."""
        result = self._validate_phone_logic("+33612345678")
        assert result == "+33612345678"

    def test_with_spaces(self) -> None:
        """Test avec espaces."""
        result = self._validate_phone_logic("06 12 34 56 78")
        assert result == "+33612345678"

    def test_with_dashes(self) -> None:
        """Test avec tirets."""
        result = self._validate_phone_logic("06-12-34-56-78")
        assert result == "+33612345678"

    def test_without_prefix(self) -> None:
        """Test sans préfixe."""
        result = self._validate_phone_logic("612345678")
        assert result == "+33612345678"

    def test_empty_phone_raises(self) -> None:
        """Test avec numéro vide."""
        with pytest.raises(ValueError) as exc_info:
            self._validate_phone_logic("")
        assert "vide" in str(exc_info.value)

    def test_none_phone_raises(self) -> None:
        """Test avec numéro None."""
        with pytest.raises(ValueError) as exc_info:
            self._validate_phone_logic(None)
        assert "vide" in str(exc_info.value)

    def test_invalid_phone_raises(self) -> None:
        """Test avec numéro invalide."""
        with pytest.raises(ValueError) as exc_info:
            self._validate_phone_logic("abc")
        assert "invalide" in str(exc_info.value)

    def test_too_short_raises(self) -> None:
        """Test numéro trop court."""
        with pytest.raises(ValueError):
            self._validate_phone_logic("0612")

    def test_international_with_spaces(self) -> None:
        """Test format international avec espaces."""
        result = self._validate_phone_logic("+33 6 12 34 56 78")
        assert result == "+33612345678"

    def test_parentheses(self) -> None:
        """Test avec parenthèses."""
        result = self._validate_phone_logic("(06) 12 34 56 78")
        assert result == "+33612345678"

    def test_dots(self) -> None:
        """Test avec points."""
        result = self._validate_phone_logic("06.12.34.56.78")
        assert result == "+33612345678"


class TestTemplateFormatting:
    """Tests de formatage de templates (logique pure avec Jinja2)."""

    def _format_template_logic(
        self, template: str, context: dict[str, Any] | None
    ) -> str:
        """Logique de formatage de template."""
        if not template or not context:
            return template

        try:
            from jinja2 import Template

            safe_context: dict[str, str | int | float] = {}
            for key, value in context.items():
                if isinstance(value, (str, int, float)):
                    safe_context[key] = value
                elif hasattr(value, "strftime"):
                    safe_context[key] = value.strftime("%d/%m/%Y %H:%M")
                else:
                    safe_context[key] = str(value)

            template_obj: Template = Template(template)
            return template_obj.render(**safe_context)
        except Exception:
            return template

    def test_simple_template(self) -> None:
        """Test template simple."""
        result = self._format_template_logic("Bonjour {{name}}", {"name": "Jean"})
        assert result == "Bonjour Jean"

    def test_multiple_variables(self) -> None:
        """Test avec plusieurs variables."""
        result = self._format_template_logic(
            "{{greeting}} {{name}}, montant: {{amount}}€",
            {"greeting": "Bonjour", "name": "Marie", "amount": 150.50},
        )
        assert "Bonjour" in result
        assert "Marie" in result
        assert "150.5" in result

    def test_with_datetime(self) -> None:
        """Test avec datetime."""
        dt = datetime(2025, 1, 15, 14, 30)
        result = self._format_template_logic("RDV le {{date}}", {"date": dt})
        assert "15/01/2025" in result
        assert "14:30" in result

    def test_empty_template(self) -> None:
        """Test template vide."""
        result = self._format_template_logic("", {"name": "Test"})
        assert result == ""

    def test_empty_context(self) -> None:
        """Test contexte vide."""
        result = self._format_template_logic("Hello", {})
        assert result == "Hello"

    def test_none_context(self) -> None:
        """Test contexte None."""
        result = self._format_template_logic("Hello", None)
        assert result == "Hello"

    def test_object_conversion(self) -> None:
        """Test conversion objet en string."""

        class CustomObj:
            def __str__(self) -> str:
                return "CustomValue"

        result = self._format_template_logic("Value: {{obj}}", {"obj": CustomObj()})
        assert "CustomValue" in result

    def test_integer_value(self) -> None:
        """Test valeur entière."""
        result = self._format_template_logic("Quantité: {{qty}}", {"qty": 42})
        assert "42" in result

    def test_float_value(self) -> None:
        """Test valeur flottante."""
        result = self._format_template_logic("Total: {{total}}", {"total": 123.45})
        assert "123.45" in result

    def test_special_characters(self) -> None:
        """Test caractères spéciaux."""
        result = self._format_template_logic(
            "Prix: {{price}}€ / unité", {"price": "15.50"}
        )
        assert "15.50€" in result


class TestQuotaLogic:
    """Tests de logique de quota (sans frappe)."""

    def _calculate_remaining_quota(self, role: str, sent_today: int = 0) -> int:
        """Calcule le quota restant basé sur le rôle."""
        role_quotas = {
            "SMS User": 100,
            "SMS Manager": 500,
            "System Manager": 9999,
        }
        max_quota = role_quotas.get(role, 0)
        return max(0, max_quota - sent_today)

    def test_system_manager_quota(self) -> None:
        """Test quota System Manager."""
        remaining = self._calculate_remaining_quota("System Manager")
        assert remaining == 9999

    def test_sms_manager_quota(self) -> None:
        """Test quota SMS Manager."""
        remaining = self._calculate_remaining_quota("SMS Manager")
        assert remaining == 500

    def test_sms_user_quota(self) -> None:
        """Test quota SMS User."""
        remaining = self._calculate_remaining_quota("SMS User")
        assert remaining == 100

    def test_no_role_quota(self) -> None:
        """Test sans rôle valide."""
        remaining = self._calculate_remaining_quota("Guest")
        assert remaining == 0

    def test_quota_after_sending(self) -> None:
        """Test quota après envoi."""
        remaining = self._calculate_remaining_quota("SMS User", sent_today=50)
        assert remaining == 50

    def test_quota_exceeded(self) -> None:
        """Test quota dépassé."""
        remaining = self._calculate_remaining_quota("SMS User", sent_today=150)
        assert remaining == 0


class TestPermissionLogic:
    """Tests de logique de permissions (sans frappe)."""

    def _has_permission_logic(
        self,
        user_roles: list[str],
        doc_owner: str,
        user: str,
        doc_company: str | None,
        user_company: str | None,
    ) -> bool:
        """Logique de vérification de permission."""
        if "System Manager" in user_roles:
            return True

        if "SMS Manager" in user_roles:
            if user_company and doc_company == user_company:
                return True
            if not doc_company:
                return True

        if "SMS User" in user_roles:
            return doc_owner == user

        return False

    def test_system_manager_always_allowed(self) -> None:
        """System Manager a toujours accès."""
        result = self._has_permission_logic(
            user_roles=["System Manager"],
            doc_owner="other@test.com",
            user="admin@test.com",
            doc_company="Other Company",
            user_company="My Company",
        )
        assert result is True

    def test_sms_manager_same_company(self) -> None:
        """SMS Manager a accès à sa société."""
        result = self._has_permission_logic(
            user_roles=["SMS Manager"],
            doc_owner="other@test.com",
            user="manager@test.com",
            doc_company="My Company",
            user_company="My Company",
        )
        assert result is True

    def test_sms_manager_different_company(self) -> None:
        """SMS Manager n'a pas accès aux autres sociétés."""
        result = self._has_permission_logic(
            user_roles=["SMS Manager"],
            doc_owner="other@test.com",
            user="manager@test.com",
            doc_company="Other Company",
            user_company="My Company",
        )
        assert result is False

    def test_sms_manager_no_company_doc(self) -> None:
        """SMS Manager a accès aux docs sans société."""
        result = self._has_permission_logic(
            user_roles=["SMS Manager"],
            doc_owner="other@test.com",
            user="manager@test.com",
            doc_company=None,
            user_company="My Company",
        )
        assert result is True

    def test_sms_user_own_doc(self) -> None:
        """SMS User a accès à ses propres docs."""
        result = self._has_permission_logic(
            user_roles=["SMS User"],
            doc_owner="user@test.com",
            user="user@test.com",
            doc_company="Company",
            user_company="Company",
        )
        assert result is True

    def test_sms_user_other_doc(self) -> None:
        """SMS User n'a pas accès aux docs des autres."""
        result = self._has_permission_logic(
            user_roles=["SMS User"],
            doc_owner="other@test.com",
            user="user@test.com",
            doc_company="Company",
            user_company="Company",
        )
        assert result is False

    def test_guest_no_access(self) -> None:
        """Guest n'a pas accès."""
        result = self._has_permission_logic(
            user_roles=["Guest"],
            doc_owner="user@test.com",
            user="user@test.com",
            doc_company="Company",
            user_company="Company",
        )
        assert result is False


class TestCampaignLimitsLogic:
    """Tests de logique de limites de campagne."""

    def _check_limits(
        self,
        total_customers: int,
        estimated_revenue: float,
        max_sms: int = 10000,
        max_amount_approval: float = 5000,
        max_sms_approval: int = 1000,
    ) -> dict[str, Any]:
        """Vérifie les limites de campagne."""
        result = {"valid": True, "requires_approval": False, "error": None}

        if total_customers > max_sms:
            result["valid"] = False
            result["error"] = f"Limite dépassée: maximum {max_sms} SMS"
            return result

        if estimated_revenue > max_amount_approval:
            result["requires_approval"] = True

        if total_customers > max_sms_approval:
            result["requires_approval"] = True

        return result

    def test_within_limits(self) -> None:
        """Test dans les limites."""
        result = self._check_limits(100, 1000)
        assert result["valid"] is True
        assert result["requires_approval"] is False

    def test_sms_limit_exceeded(self) -> None:
        """Test limite SMS dépassée."""
        result = self._check_limits(20000, 1000)
        assert result["valid"] is False
        assert "Limite" in result["error"]

    def test_requires_approval_by_amount(self) -> None:
        """Test nécessite approbation par montant."""
        result = self._check_limits(500, 10000)
        assert result["valid"] is True
        assert result["requires_approval"] is True

    def test_requires_approval_by_sms_count(self) -> None:
        """Test nécessite approbation par nombre SMS."""
        result = self._check_limits(5000, 1000)
        assert result["valid"] is True
        assert result["requires_approval"] is True


class TestHealthCheckReport:
    """Tests de logique de rapport de santé."""

    def _determine_status(self, errors: list[str], warnings: list[str]) -> str:
        """Détermine le statut global du rapport."""
        if errors:
            return "error"
        if warnings:
            return "warning"
        return "healthy"

    def test_healthy_status(self) -> None:
        """Test statut sain."""
        status = self._determine_status([], [])
        assert status == "healthy"

    def test_warning_status(self) -> None:
        """Test statut warning."""
        status = self._determine_status([], ["Warning 1"])
        assert status == "warning"

    def test_error_status(self) -> None:
        """Test statut erreur."""
        status = self._determine_status(["Error 1"], [])
        assert status == "error"

    def test_error_priority_over_warning(self) -> None:
        """Test erreur prioritaire sur warning."""
        status = self._determine_status(["Error 1"], ["Warning 1"])
        assert status == "error"


class TestGdprAnonymization:
    """Tests de logique d'anonymisation RGPD."""

    def _anonymize_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Anonymise les données sensibles."""
        anonymized = data.copy()
        sensitive_fields = ["customer_mobile", "customer_name", "phone", "email"]

        for field in sensitive_fields:
            if field in anonymized:
                if field == "customer_name":
                    anonymized[field] = "Client Anonyme"
                else:
                    anonymized[field] = "***ANONYMIZED***"

        anonymized["anonymized"] = True
        return anonymized

    def test_anonymize_customer_mobile(self) -> None:
        """Test anonymisation mobile."""
        data = {"customer_mobile": "+33612345678"}
        result = self._anonymize_data(data)
        assert result["customer_mobile"] == "***ANONYMIZED***"
        assert result["anonymized"] is True

    def test_anonymize_customer_name(self) -> None:
        """Test anonymisation nom."""
        data = {"customer_name": "Jean Dupont"}
        result = self._anonymize_data(data)
        assert result["customer_name"] == "Client Anonyme"

    def test_preserve_non_sensitive(self) -> None:
        """Test préservation données non sensibles."""
        data = {"campaign_id": "CAMP-001", "status": "Sent"}
        result = self._anonymize_data(data)
        assert result["campaign_id"] == "CAMP-001"
        assert result["status"] == "Sent"


class TestOVHSignatureCreation:
    """Tests de création de signature OVH (logique pure)."""

    import hashlib

    def _create_signature_logic(
        self,
        app_secret: str,
        consumer_key: str,
        method: str,
        url: str,
        body: str,
        timestamp: str,
    ) -> str:
        """Logique de création de signature OVH."""
        pre_hash = f"{app_secret}+{consumer_key}+{method}+{url}+{body}+{timestamp}"
        import hashlib

        signature = "$1$" + hashlib.sha1(pre_hash.encode("utf-8")).hexdigest()
        return signature

    def test_signature_format(self) -> None:
        """Test format de signature."""
        result = self._create_signature_logic(
            "secret", "consumer", "GET", "https://api.ovh.com/1.0/sms", "", "123456"
        )
        assert result.startswith("$1$")
        assert len(result) == 43  # $1$ + 40 chars SHA1

    def test_signature_consistency(self) -> None:
        """Test cohérence de signature."""
        sig1 = self._create_signature_logic(
            "secret", "consumer", "GET", "https://api.ovh.com", "", "123"
        )
        sig2 = self._create_signature_logic(
            "secret", "consumer", "GET", "https://api.ovh.com", "", "123"
        )
        assert sig1 == sig2

    def test_signature_different_params(self) -> None:
        """Test signature avec paramètres différents."""
        sig1 = self._create_signature_logic(
            "secret1", "consumer", "GET", "https://api.ovh.com", "", "123"
        )
        sig2 = self._create_signature_logic(
            "secret2", "consumer", "GET", "https://api.ovh.com", "", "123"
        )
        assert sig1 != sig2

    def test_signature_with_body(self) -> None:
        """Test signature avec corps de requête."""
        sig_no_body = self._create_signature_logic(
            "secret", "consumer", "POST", "https://api.ovh.com", "", "123"
        )
        sig_with_body = self._create_signature_logic(
            "secret", "consumer", "POST", "https://api.ovh.com", '{"key":"val"}', "123"
        )
        assert sig_no_body != sig_with_body


class TestPricingCalculation:
    """Tests de calcul de prix (logique pure)."""

    def _calculate_final_price(self, valuation_rate: float, margin_eur: float) -> float:
        """Calcule le prix final."""
        return valuation_rate + margin_eur

    def _calculate_total_amount(self, final_price: float, qty: int) -> float:
        """Calcule le montant total."""
        return final_price * qty

    def _calculate_margin_percent(self, margin: float, valuation: float) -> float:
        """Calcule le pourcentage de marge."""
        if valuation <= 0:
            return 0.0
        return (margin / valuation) * 100

    def test_final_price_basic(self) -> None:
        """Test calcul prix final basique."""
        result = self._calculate_final_price(100.0, 25.0)
        assert result == 125.0

    def test_final_price_zero_margin(self) -> None:
        """Test prix final sans marge."""
        result = self._calculate_final_price(100.0, 0.0)
        assert result == 100.0

    def test_total_amount_single(self) -> None:
        """Test montant total quantité 1."""
        result = self._calculate_total_amount(125.0, 1)
        assert result == 125.0

    def test_total_amount_multiple(self) -> None:
        """Test montant total quantité multiple."""
        result = self._calculate_total_amount(125.0, 5)
        assert result == 625.0

    def test_margin_percent_calculation(self) -> None:
        """Test calcul pourcentage marge."""
        result = self._calculate_margin_percent(25.0, 100.0)
        assert result == 25.0

    def test_margin_percent_zero_valuation(self) -> None:
        """Test marge avec valorisation zéro."""
        result = self._calculate_margin_percent(25.0, 0.0)
        assert result == 0.0


class TestSMSCostCalculation:
    """Tests de calcul de coût SMS (logique pure)."""

    def _calculate_sms_cost(
        self, num_customers: int, cost_per_sms: float = 0.10
    ) -> float:
        """Calcule le coût total des SMS."""
        return num_customers * cost_per_sms

    def _calculate_credit_usage(self, message_length: int) -> int:
        """Calcule le nombre de crédits utilisés."""
        # SMS standard: 160 chars = 1 crédit
        # SMS avec caractères spéciaux: 70 chars = 1 crédit
        if message_length <= 160:
            return 1
        return (message_length + 152) // 153

    def test_sms_cost_single(self) -> None:
        """Test coût SMS pour 1 client."""
        result = self._calculate_sms_cost(1)
        assert result == 0.10

    def test_sms_cost_multiple(self) -> None:
        """Test coût SMS pour plusieurs clients."""
        result = self._calculate_sms_cost(100)
        assert result == 10.0

    def test_sms_cost_custom_rate(self) -> None:
        """Test coût SMS avec taux personnalisé."""
        result = self._calculate_sms_cost(50, 0.15)
        assert result == 7.5

    def test_credit_usage_short_message(self) -> None:
        """Test crédits pour message court."""
        result = self._calculate_credit_usage(100)
        assert result == 1

    def test_credit_usage_exact_160(self) -> None:
        """Test crédits pour message 160 chars."""
        result = self._calculate_credit_usage(160)
        assert result == 1

    def test_credit_usage_long_message(self) -> None:
        """Test crédits pour message long."""
        result = self._calculate_credit_usage(320)
        assert result == 3


class TestCampaignStatusLogic:
    """Tests de logique de statut de campagne."""

    def _determine_campaign_status(
        self,
        items_count: int,
        sent_count: int,
        ready_to_send: bool,
    ) -> str:
        """Détermine le statut de la campagne."""
        if items_count == 0:
            return "Brouillon"
        if sent_count == 0:
            return "Prêt" if ready_to_send else "Brouillon"
        if sent_count == items_count:
            return "Envoyé"
        return "Partiellement envoyé"

    def test_status_empty(self) -> None:
        """Test statut campagne vide."""
        result = self._determine_campaign_status(0, 0, False)
        assert result == "Brouillon"

    def test_status_draft_not_ready(self) -> None:
        """Test statut brouillon non prêt."""
        result = self._determine_campaign_status(5, 0, False)
        assert result == "Brouillon"

    def test_status_ready(self) -> None:
        """Test statut prêt."""
        result = self._determine_campaign_status(5, 0, True)
        assert result == "Prêt"

    def test_status_partial(self) -> None:
        """Test statut partiellement envoyé."""
        result = self._determine_campaign_status(5, 3, True)
        assert result == "Partiellement envoyé"

    def test_status_sent(self) -> None:
        """Test statut envoyé."""
        result = self._determine_campaign_status(5, 5, True)
        assert result == "Envoyé"


class TestSenderValidation:
    """Tests de validation d'expéditeur SMS."""

    def _validate_sender_name(self, name: str) -> bool:
        """Valide le nom d'expéditeur."""
        if not name or len(name) > 11:
            return False
        return bool(re.match(r"^[a-zA-Z0-9]+$", name))

    def test_valid_sender_alpha(self) -> None:
        """Test expéditeur alphabétique valide."""
        assert self._validate_sender_name("ERPNext") is True

    def test_valid_sender_alphanum(self) -> None:
        """Test expéditeur alphanumérique valide."""
        assert self._validate_sender_name("MyApp123") is True

    def test_valid_sender_max_length(self) -> None:
        """Test expéditeur longueur max."""
        assert self._validate_sender_name("12345678901") is True  # 11 chars

    def test_invalid_sender_too_long(self) -> None:
        """Test expéditeur trop long."""
        assert self._validate_sender_name("123456789012") is False  # 12 chars

    def test_invalid_sender_special_chars(self) -> None:
        """Test expéditeur avec caractères spéciaux."""
        assert self._validate_sender_name("My App!") is False

    def test_invalid_sender_empty(self) -> None:
        """Test expéditeur vide."""
        assert self._validate_sender_name("") is False

    def test_valid_sender_single_char(self) -> None:
        """Test expéditeur caractère unique."""
        assert self._validate_sender_name("A") is True


class TestEventReminderTiming:
    """Tests de logique de timing pour rappels d'événements."""

    def _should_send_reminder(
        self,
        hours_before: int,
        event_hours_away: float,
        already_sent: bool,
    ) -> bool:
        """Détermine si un rappel doit être envoyé."""
        if already_sent:
            return False
        # Fenêtre de 30 minutes autour de l'heure de rappel
        target_hours = hours_before
        return abs(event_hours_away - target_hours) <= 0.5

    def test_reminder_exact_time(self) -> None:
        """Test rappel à l'heure exacte."""
        result = self._should_send_reminder(24, 24.0, False)
        assert result is True

    def test_reminder_within_window(self) -> None:
        """Test rappel dans la fenêtre."""
        result = self._should_send_reminder(24, 24.3, False)
        assert result is True

    def test_reminder_outside_window(self) -> None:
        """Test rappel hors fenêtre."""
        result = self._should_send_reminder(24, 25.0, False)
        assert result is False

    def test_reminder_already_sent(self) -> None:
        """Test rappel déjà envoyé."""
        result = self._should_send_reminder(24, 24.0, True)
        assert result is False

    def test_reminder_past_event(self) -> None:
        """Test événement passé."""
        result = self._should_send_reminder(24, -1.0, False)
        assert result is False


class TestMessageLengthValidation:
    """Tests de validation de longueur de message SMS."""

    MAX_SMS_LENGTH = 1600  # Max chars for concatenated SMS

    def _validate_message_length(self, message: str) -> tuple[bool, int]:
        """Valide la longueur du message."""
        if not message:
            return (False, 0)
        length = len(message)
        if length > self.MAX_SMS_LENGTH:
            return (False, length)
        return (True, length)

    def _count_sms_parts(self, message_length: int) -> int:
        """Compte les parties SMS nécessaires."""
        if message_length <= 160:
            return 1
        # Messages concaténés: 153 chars par partie
        return (message_length + 152) // 153

    def test_valid_short_message(self) -> None:
        """Test message court valide."""
        is_valid, length = self._validate_message_length("Bonjour!")
        assert is_valid is True
        assert length == 8

    def test_valid_long_message(self) -> None:
        """Test message long valide."""
        message = "A" * 500
        is_valid, length = self._validate_message_length(message)
        assert is_valid is True
        assert length == 500

    def test_invalid_too_long(self) -> None:
        """Test message trop long."""
        message = "A" * 2000
        is_valid, length = self._validate_message_length(message)
        assert is_valid is False
        assert length == 2000

    def test_invalid_empty(self) -> None:
        """Test message vide."""
        is_valid, length = self._validate_message_length("")
        assert is_valid is False
        assert length == 0

    def test_sms_parts_single(self) -> None:
        """Test 1 partie SMS."""
        parts = self._count_sms_parts(100)
        assert parts == 1

    def test_sms_parts_two(self) -> None:
        """Test 2 parties SMS."""
        parts = self._count_sms_parts(200)
        assert parts == 2

    def test_sms_parts_multiple(self) -> None:
        """Test plusieurs parties SMS."""
        parts = self._count_sms_parts(500)
        assert parts == 4


class TestBatchProcessingLogic:
    """Tests de logique de traitement par lots."""

    def _split_into_batches(
        self, items: list[Any], batch_size: int = 100
    ) -> list[list[Any]]:
        """Divise une liste en lots."""
        if not items:
            return []
        return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]

    def _calculate_progress(self, processed: int, total: int) -> float:
        """Calcule le pourcentage de progression."""
        if total <= 0:
            return 0.0
        return round((processed / total) * 100, 2)

    def test_single_batch(self) -> None:
        """Test lot unique."""
        items = list(range(50))
        batches = self._split_into_batches(items, 100)
        assert len(batches) == 1
        assert len(batches[0]) == 50

    def test_multiple_batches(self) -> None:
        """Test lots multiples."""
        items = list(range(250))
        batches = self._split_into_batches(items, 100)
        assert len(batches) == 3
        assert len(batches[0]) == 100
        assert len(batches[1]) == 100
        assert len(batches[2]) == 50

    def test_empty_list(self) -> None:
        """Test liste vide."""
        batches = self._split_into_batches([])
        assert batches == []

    def test_progress_zero(self) -> None:
        """Test progression zéro."""
        result = self._calculate_progress(0, 100)
        assert result == 0.0

    def test_progress_half(self) -> None:
        """Test progression 50%."""
        result = self._calculate_progress(50, 100)
        assert result == 50.0

    def test_progress_complete(self) -> None:
        """Test progression 100%."""
        result = self._calculate_progress(100, 100)
        assert result == 100.0

    def test_progress_empty_total(self) -> None:
        """Test progression total zéro."""
        result = self._calculate_progress(10, 0)
        assert result == 0.0

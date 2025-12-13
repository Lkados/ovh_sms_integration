# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module sms_pricing_campaign.py.

Ce module teste les fonctions de campagnes de tarification SMS.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestFormatPhoneNumber:
    """Tests pour la méthode format_phone_number."""

    def test_format_french_mobile(self) -> None:
        """Test format mobile français."""
        from ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign import (
            SMSPricingCampaign,
        )

        campaign = MagicMock(spec=SMSPricingCampaign)

        result = SMSPricingCampaign.format_phone_number(campaign, "0612345678")
        assert result == "+33612345678"

    def test_format_with_spaces(self) -> None:
        """Test format avec espaces."""
        from ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign import (
            SMSPricingCampaign,
        )

        campaign = MagicMock(spec=SMSPricingCampaign)

        result = SMSPricingCampaign.format_phone_number(campaign, "06 12 34 56 78")
        assert result == "+33612345678"

    def test_format_international(self) -> None:
        """Test format international."""
        from ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign import (
            SMSPricingCampaign,
        )

        campaign = MagicMock(spec=SMSPricingCampaign)

        result = SMSPricingCampaign.format_phone_number(campaign, "+33612345678")
        assert result == "+33612345678"

    def test_format_none(self) -> None:
        """Test format None."""
        from ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign import (
            SMSPricingCampaign,
        )

        campaign = MagicMock(spec=SMSPricingCampaign)

        result = SMSPricingCampaign.format_phone_number(campaign, None)
        assert result is None

    def test_format_with_dots(self) -> None:
        """Test format avec points."""
        from ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign import (
            SMSPricingCampaign,
        )

        campaign = MagicMock(spec=SMSPricingCampaign)

        result = SMSPricingCampaign.format_phone_number(campaign, "06.12.34.56.78")
        assert result == "+33612345678"


class TestCalculateItemPricing:
    """Tests pour la méthode calculate_item_pricing."""

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign.frappe"
    )
    def test_calculate_pricing_basic(self, mock_frappe: MagicMock) -> None:
        """Test calcul prix basique."""
        from ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign import (
            SMSPricingCampaign,
        )

        campaign = MagicMock(spec=SMSPricingCampaign)

        item = MagicMock()
        item.valuation_rate = 100.0
        item.margin_amount_eur = 25.0
        item.qty = 1

        SMSPricingCampaign.calculate_item_pricing(campaign, item)

        assert item.final_price == 125.0
        assert item.amount == 125.0

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign.frappe"
    )
    def test_calculate_pricing_with_quantity(self, mock_frappe: MagicMock) -> None:
        """Test calcul prix avec quantité."""
        from ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign import (
            SMSPricingCampaign,
        )

        campaign = MagicMock(spec=SMSPricingCampaign)

        item = MagicMock()
        item.valuation_rate = 100.0
        item.margin_amount_eur = 25.0
        item.qty = 5

        SMSPricingCampaign.calculate_item_pricing(campaign, item)

        assert item.final_price == 125.0
        assert item.amount == 625.0

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign.frappe"
    )
    def test_calculate_pricing_no_margin(self, mock_frappe: MagicMock) -> None:
        """Test calcul prix sans marge."""
        from ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign import (
            SMSPricingCampaign,
        )

        campaign = MagicMock(spec=SMSPricingCampaign)

        item = MagicMock()
        item.valuation_rate = 100.0
        item.margin_amount_eur = 0
        item.qty = 1

        SMSPricingCampaign.calculate_item_pricing(campaign, item)

        assert item.final_price == 100.0
        assert item.amount == 100.0


class TestCalculateTotals:
    """Tests pour la méthode calculate_totals."""

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign.frappe"
    )
    def test_calculate_totals_basic(self, mock_frappe: MagicMock) -> None:
        """Test calcul totaux basique."""
        from ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign import (
            SMSPricingCampaign,
        )

        campaign = MagicMock(spec=SMSPricingCampaign)

        item1 = MagicMock()
        item1.customer = "Customer-001"
        item1.amount = 125.0
        item1.margin_amount_eur = 25.0
        item1.valuation_rate = 100.0
        item1.qty = 1

        item2 = MagicMock()
        item2.customer = "Customer-002"
        item2.amount = 250.0
        item2.margin_amount_eur = 50.0
        item2.valuation_rate = 200.0
        item2.qty = 1

        campaign.pricing_items = [item1, item2]

        SMSPricingCampaign.calculate_totals(campaign)

        assert campaign.total_items == 2
        assert campaign.total_customers == 2
        assert campaign.total_sms_cost == 0.2
        assert campaign.estimated_revenue == 375.0
        assert campaign.profit_potential == 75.0

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign.frappe"
    )
    def test_calculate_totals_same_customer(self, mock_frappe: MagicMock) -> None:
        """Test calcul totaux avec même client."""
        from ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign import (
            SMSPricingCampaign,
        )

        campaign = MagicMock(spec=SMSPricingCampaign)

        item1 = MagicMock()
        item1.customer = "Customer-001"
        item1.amount = 100.0
        item1.margin_amount_eur = 20.0
        item1.valuation_rate = 80.0
        item1.qty = 1

        item2 = MagicMock()
        item2.customer = "Customer-001"  # Same customer
        item2.amount = 200.0
        item2.margin_amount_eur = 40.0
        item2.valuation_rate = 160.0
        item2.qty = 1

        campaign.pricing_items = [item1, item2]

        SMSPricingCampaign.calculate_totals(campaign)

        assert campaign.total_items == 2
        assert campaign.total_customers == 1  # Only 1 unique customer
        assert campaign.total_sms_cost == 0.1

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign.frappe"
    )
    def test_calculate_totals_empty(self, mock_frappe: MagicMock) -> None:
        """Test calcul totaux vide."""
        from ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign import (
            SMSPricingCampaign,
        )

        campaign = MagicMock(spec=SMSPricingCampaign)
        campaign.pricing_items = []

        SMSPricingCampaign.calculate_totals(campaign)

        # Should not set any values


class TestValidateReadyToSend:
    """Tests pour la méthode validate_ready_to_send."""

    def test_ready_to_send_valid(self) -> None:
        """Test campagne prête à envoyer."""
        from ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign import (
            SMSPricingCampaign,
        )

        campaign = MagicMock(spec=SMSPricingCampaign)

        item = MagicMock()
        item.customer_mobile = "+33612345678"
        item.final_price = 125.0

        campaign.pricing_items = [item]

        result = SMSPricingCampaign.validate_ready_to_send(campaign)

        assert result is True

    def test_ready_to_send_no_mobile(self) -> None:
        """Test campagne sans mobile."""
        from ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign import (
            SMSPricingCampaign,
        )

        campaign = MagicMock(spec=SMSPricingCampaign)

        item = MagicMock()
        item.customer_mobile = None
        item.final_price = 125.0

        campaign.pricing_items = [item]

        result = SMSPricingCampaign.validate_ready_to_send(campaign)

        assert result is False

    def test_ready_to_send_no_price(self) -> None:
        """Test campagne sans prix."""
        from ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign import (
            SMSPricingCampaign,
        )

        campaign = MagicMock(spec=SMSPricingCampaign)

        item = MagicMock()
        item.customer_mobile = "+33612345678"
        item.final_price = None

        campaign.pricing_items = [item]

        result = SMSPricingCampaign.validate_ready_to_send(campaign)

        assert result is False

    def test_ready_to_send_empty(self) -> None:
        """Test campagne vide."""
        from ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign import (
            SMSPricingCampaign,
        )

        campaign = MagicMock(spec=SMSPricingCampaign)
        campaign.pricing_items = []

        result = SMSPricingCampaign.validate_ready_to_send(campaign)

        assert result is False


class TestUpdateStatus:
    """Tests pour la méthode update_status."""

    def test_status_brouillon_empty(self) -> None:
        """Test statut brouillon si vide."""
        from ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign import (
            SMSPricingCampaign,
        )

        campaign = MagicMock(spec=SMSPricingCampaign)
        campaign.pricing_items = []

        SMSPricingCampaign.update_status(campaign)

        assert campaign.status == "Brouillon"

    def test_status_pret(self) -> None:
        """Test statut prêt."""
        from ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign import (
            SMSPricingCampaign,
        )

        campaign = MagicMock(spec=SMSPricingCampaign)

        item = MagicMock()
        item.sms_sent = False
        item.customer_mobile = "+33612345678"
        item.final_price = 125.0

        campaign.pricing_items = [item]
        campaign.validate_ready_to_send.return_value = True

        SMSPricingCampaign.update_status(campaign)

        assert campaign.status == "Prêt"

    def test_status_envoye(self) -> None:
        """Test statut envoyé."""
        from ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign import (
            SMSPricingCampaign,
        )

        campaign = MagicMock(spec=SMSPricingCampaign)

        item = MagicMock()
        item.sms_sent = True

        campaign.pricing_items = [item]

        SMSPricingCampaign.update_status(campaign)

        assert campaign.status == "Envoyé"

    def test_status_partiellement_envoye(self) -> None:
        """Test statut partiellement envoyé."""
        from ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign import (
            SMSPricingCampaign,
        )

        campaign = MagicMock(spec=SMSPricingCampaign)

        item1 = MagicMock()
        item1.sms_sent = True

        item2 = MagicMock()
        item2.sms_sent = False

        campaign.pricing_items = [item1, item2]

        SMSPricingCampaign.update_status(campaign)

        assert campaign.status == "Partiellement envoyé"


class TestFormatSMSMessage:
    """Tests pour la méthode format_sms_message."""

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign.frappe"
    )
    def test_format_message_basic(self, mock_frappe: MagicMock) -> None:
        """Test formatage message basique."""
        from ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign import (
            SMSPricingCampaign,
        )

        campaign = MagicMock(spec=SMSPricingCampaign)
        campaign.sms_template = (
            "Bonjour {{customer_name}}, {{item_name}} à {{final_price}}€"
        )
        campaign.company = "My Company"
        campaign.title = "Test Campaign"

        item = MagicMock()
        item.customer_name = "ACME Corp"
        item.customer = "ACME"
        item.item_name = "Fuel Oil"
        item.item_code = "FUEL-001"
        item.final_price = 150.50
        item.amount = 150.50
        item.valuation_rate = 120.00
        item.margin_amount_eur = 30.50
        item.qty = 1

        result = SMSPricingCampaign.format_sms_message(campaign, item)

        assert "ACME Corp" in result
        assert "Fuel Oil" in result
        assert "150.50" in result

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign.frappe"
    )
    def test_format_message_default_template(self, mock_frappe: MagicMock) -> None:
        """Test formatage avec template par défaut."""
        from ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign import (
            SMSPricingCampaign,
        )

        mock_frappe.defaults.get_user_default.return_value = "Default Company"

        campaign = MagicMock(spec=SMSPricingCampaign)
        campaign.sms_template = None
        campaign.company = None
        campaign.title = None

        item = MagicMock()
        item.customer_name = "Test Client"
        item.customer = "TEST"
        item.item_name = "Product"
        item.item_code = "PROD-001"
        item.final_price = 100.0
        item.amount = 100.0
        item.valuation_rate = 80.0
        item.margin_amount_eur = 20.0
        item.qty = 1

        result = SMSPricingCampaign.format_sms_message(campaign, item)

        assert "Test Client" in result
        assert "Product" in result
        assert "100.00" in result


class TestSendSMSToItem:
    """Tests pour la méthode send_sms_to_item."""

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign.frappe"
    )
    def test_send_already_sent(self, mock_frappe: MagicMock) -> None:
        """Test envoi déjà effectué."""
        from ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign import (
            SMSPricingCampaign,
        )

        mock_frappe._ = lambda x: x

        campaign = MagicMock(spec=SMSPricingCampaign)

        item = MagicMock()
        item.sms_sent = True

        result = SMSPricingCampaign.send_sms_to_item(campaign, item)

        assert result["success"] is False
        assert "déjà envoyé" in result["message"]

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign.frappe"
    )
    def test_send_no_mobile(self, mock_frappe: MagicMock) -> None:
        """Test envoi sans mobile."""
        from ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign import (
            SMSPricingCampaign,
        )

        mock_frappe._ = lambda x: x

        campaign = MagicMock(spec=SMSPricingCampaign)

        item = MagicMock()
        item.sms_sent = False
        item.customer_mobile = None

        result = SMSPricingCampaign.send_sms_to_item(campaign, item)

        assert result["success"] is False
        assert "mobile manquant" in result["message"]

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign.frappe"
    )
    def test_send_disabled(self, mock_frappe: MagicMock) -> None:
        """Test envoi avec intégration désactivée."""
        from ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign import (
            SMSPricingCampaign,
        )

        mock_frappe._ = lambda x: x

        mock_settings = MagicMock()
        mock_settings.enabled = False
        mock_frappe.get_single.return_value = mock_settings

        campaign = MagicMock(spec=SMSPricingCampaign)
        campaign.format_sms_message.return_value = "Test message"

        item = MagicMock()
        item.sms_sent = False
        item.customer_mobile = "+33612345678"

        result = SMSPricingCampaign.send_sms_to_item(campaign, item)

        assert result["success"] is False
        assert "non activé" in result["message"]

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign.frappe"
    )
    def test_send_success(self, mock_frappe: MagicMock) -> None:
        """Test envoi réussi."""
        from ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign import (
            SMSPricingCampaign,
        )

        mock_frappe._ = lambda x: x

        mock_settings = MagicMock()
        mock_settings.enabled = True
        mock_settings.send_sms.return_value = {"success": True}
        mock_frappe.get_single.return_value = mock_settings

        campaign = MagicMock(spec=SMSPricingCampaign)
        campaign.format_sms_message.return_value = "Test message"

        item = MagicMock()
        item.sms_sent = False
        item.customer_mobile = "+33612345678"

        result = SMSPricingCampaign.send_sms_to_item(campaign, item)

        assert result["success"] is True
        assert item.sms_sent == 1
        assert item.sms_status == "Envoyé"


class TestValidate:
    """Tests pour la méthode validate."""

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign.frappe"
    )
    def test_validate_empty_items(self, mock_frappe: MagicMock) -> None:
        """Test validation sans articles."""
        from ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign import (
            SMSPricingCampaign,
        )

        mock_frappe.throw.side_effect = Exception(
            "Veuillez ajouter au moins un article"
        )

        campaign = MagicMock(spec=SMSPricingCampaign)
        campaign.pricing_items = []

        with pytest.raises(Exception):
            SMSPricingCampaign.validate(campaign)


class TestValidatePricingItem:
    """Tests pour la méthode validate_pricing_item."""

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign.frappe"
    )
    def test_validate_item_no_customer(self, mock_frappe: MagicMock) -> None:
        """Test validation sans client."""
        from ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign import (
            SMSPricingCampaign,
        )

        mock_frappe.throw.side_effect = Exception("Client requis")

        campaign = MagicMock(spec=SMSPricingCampaign)

        item = MagicMock()
        item.customer = None
        item.idx = 1

        with pytest.raises(Exception):
            SMSPricingCampaign.validate_pricing_item(campaign, item)

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign.frappe"
    )
    def test_validate_item_no_item_code(self, mock_frappe: MagicMock) -> None:
        """Test validation sans code article."""
        from ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign import (
            SMSPricingCampaign,
        )

        mock_frappe.throw.side_effect = Exception("Article requis")

        campaign = MagicMock(spec=SMSPricingCampaign)

        item = MagicMock()
        item.customer = "Customer-001"
        item.item_code = None
        item.idx = 1

        with pytest.raises(Exception):
            SMSPricingCampaign.validate_pricing_item(campaign, item)

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign.frappe"
    )
    def test_validate_item_negative_margin(self, mock_frappe: MagicMock) -> None:
        """Test validation avec marge négative."""
        from ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign import (
            SMSPricingCampaign,
        )

        mock_frappe.throw.side_effect = Exception("La marge ne peut pas être négative")

        campaign = MagicMock(spec=SMSPricingCampaign)
        campaign.get_customer_mobile.return_value = "+33612345678"

        item = MagicMock()
        item.customer = "Customer-001"
        item.item_code = "ITEM-001"
        item.item_name = "Test Item"
        item.customer_mobile = "+33612345678"
        item.valuation_rate = 100.0
        item.margin_amount_eur = -10.0
        item.idx = 1

        with pytest.raises(Exception):
            SMSPricingCampaign.validate_pricing_item(campaign, item)


class TestGetCustomerMobile:
    """Tests pour la méthode get_customer_mobile."""

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign.frappe"
    )
    def test_get_mobile_from_customer(self, mock_frappe: MagicMock) -> None:
        """Test récupération mobile depuis customer."""
        from ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign import (
            SMSPricingCampaign,
        )

        mock_customer = MagicMock()
        mock_customer.mobile_no = "0612345678"
        mock_frappe.get_doc.return_value = mock_customer

        campaign = MagicMock(spec=SMSPricingCampaign)
        campaign.format_phone_number.return_value = "+33612345678"

        result = SMSPricingCampaign.get_customer_mobile(campaign, "Customer-001")

        assert result == "+33612345678"

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign.frappe"
    )
    def test_get_mobile_not_found(self, mock_frappe: MagicMock) -> None:
        """Test mobile non trouvé."""
        from ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign import (
            SMSPricingCampaign,
        )

        mock_customer = MagicMock()
        mock_customer.mobile_no = None
        mock_frappe.get_doc.return_value = mock_customer
        mock_frappe.get_all.return_value = []

        campaign = MagicMock(spec=SMSPricingCampaign)

        result = SMSPricingCampaign.get_customer_mobile(campaign, "Customer-001")

        assert result is None

    @patch(
        "ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign.frappe"
    )
    def test_get_mobile_exception(self, mock_frappe: MagicMock) -> None:
        """Test avec exception."""
        from ovh_sms_integration.ovh_sms_integration.doctype.sms_pricing_campaign.sms_pricing_campaign import (
            SMSPricingCampaign,
        )

        mock_frappe.get_doc.side_effect = Exception("Customer not found")

        campaign = MagicMock(spec=SMSPricingCampaign)

        result = SMSPricingCampaign.get_customer_mobile(campaign, "Unknown-Customer")

        assert result is None

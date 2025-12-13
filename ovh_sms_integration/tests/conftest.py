# -*- coding: utf-8 -*-
"""
Configuration pytest et fixtures partagées pour les tests.

Ce module fournit des fixtures réutilisables pour tous les tests
de l'application ovh_sms_integration.
"""
from __future__ import annotations

from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_frappe() -> Generator[MagicMock, None, None]:
    """Mock complet du module frappe."""
    with patch.dict("sys.modules", {"frappe": MagicMock()}):
        import sys

        mock = sys.modules["frappe"]
        mock._ = lambda x: x
        mock.session = MagicMock()
        mock.session.user = "test@example.com"
        mock.db = MagicMock()
        mock.cache = MagicMock(return_value=MagicMock())
        mock.get_doc = MagicMock()
        mock.get_all = MagicMock(return_value=[])
        mock.get_single = MagicMock()
        mock.get_value = MagicMock()
        mock.get_cached_value = MagicMock()
        mock.get_roles = MagicMock(return_value=["System Manager"])
        mock.throw = MagicMock(side_effect=Exception)
        mock.msgprint = MagicMock()
        mock.log_error = MagicMock()
        mock.logger = MagicMock(return_value=MagicMock())
        mock.enqueue = MagicMock()
        mock.ValidationError = Exception
        mock.PermissionError = PermissionError
        mock.DoesNotExistError = Exception
        yield mock


@pytest.fixture
def mock_ovh_settings() -> dict[str, Any]:
    """Fixture pour les paramètres OVH SMS."""
    return {
        "enabled": True,
        "application_key": "test_app_key",
        "application_secret": "test_app_secret",
        "consumer_key": "test_consumer_key",
        "service_name": "sms-test-123",
        "default_sender": "TestSender",
        "test_mobile_number": "+33612345678",
    }


@pytest.fixture
def mock_employee() -> dict[str, Any]:
    """Fixture pour un employé de test."""
    return {
        "name": "EMP-001",
        "employee_name": "Jean Dupont",
        "cell_number": "+33612345678",
        "status": "Active",
        "company": "Test Company",
    }


@pytest.fixture
def mock_customer() -> dict[str, Any]:
    """Fixture pour un client de test."""
    return {
        "name": "CUST-001",
        "customer_name": "Client Test",
        "mobile_no": "+33698765432",
        "customer_type": "Individual",
    }


@pytest.fixture
def mock_event() -> dict[str, Any]:
    """Fixture pour un événement de test."""
    from datetime import datetime, timedelta

    start = datetime.now() + timedelta(hours=24)
    return {
        "name": "EVT-001",
        "subject": "Entretien chaudière",
        "starts_on": start,
        "ends_on": start + timedelta(hours=1),
        "event_type": "Private",
        "event_participants": [
            {"reference_doctype": "Customer", "reference_docname": "CUST-001"}
        ],
    }


@pytest.fixture
def mock_sms_result_success() -> dict[str, Any]:
    """Fixture pour un résultat SMS réussi."""
    return {
        "success": True,
        "message": "SMS envoyé avec succès",
        "details": {"ids": ["12345"], "totalCreditsRemoved": 1},
    }


@pytest.fixture
def mock_sms_result_failure() -> dict[str, Any]:
    """Fixture pour un résultat SMS échoué."""
    return {
        "success": False,
        "message": "Erreur d'envoi SMS",
        "details": None,
    }


@pytest.fixture
def mock_requests() -> Generator[MagicMock, None, None]:
    """Mock du module requests pour les appels API OVH."""
    with patch("requests.get") as mock_get, patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_get.return_value = mock_response
        mock_post.return_value = mock_response
        yield {"get": mock_get, "post": mock_post}


class MockFrappeDoc:
    """Classe mock pour simuler un document Frappe."""

    def __init__(self, doctype: str, data: dict[str, Any] | None = None):
        self.doctype = doctype
        self.name = data.get("name", "TEST-001") if data else "TEST-001"
        self._data = data or {}
        for key, value in self._data.items():
            setattr(self, key, value)

    def as_dict(self) -> dict[str, Any]:
        return {"doctype": self.doctype, "name": self.name, **self._data}

    def save(self) -> "MockFrappeDoc":
        return self

    def insert(self) -> "MockFrappeDoc":
        return self

    def reload(self) -> None:
        pass

    def db_set(self, field: str, value: Any) -> None:
        setattr(self, field, value)


@pytest.fixture
def mock_frappe_doc() -> type[MockFrappeDoc]:
    """Retourne la classe MockFrappeDoc pour créer des documents mock."""
    return MockFrappeDoc

"""
Shared test fixtures for UPI Fraud Detection backend tests.
Provides mocked database, Redis, ML model, and auth fixtures.
"""

import asyncio
import os
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

os.environ.update({
    "POSTGRES_HOST": os.getenv("POSTGRES_HOST", "localhost"),
    "POSTGRES_DB": os.getenv("POSTGRES_DB", "upi_fraud_test"),
    "POSTGRES_USER": os.getenv("POSTGRES_USER", "upi_user"),
    "POSTGRES_PASSWORD": os.getenv("POSTGRES_PASSWORD", "test_password_123"),
    "REDIS_URL": os.getenv("REDIS_URL", "redis://localhost:6379"),
    "SECRET_KEY": "test-secret-key-for-ci-at-least-32-chars",
    "MLFLOW_TRACKING_URI": "http://localhost:5000",
    "ADMIN_PASSWORD": "password",
    "DEBUG": "true",
})

from app.core.config import settings


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def sync_client():
    """Synchronous test client for simple tests."""
    from app.main import app

    with TestClient(app) as client:
        yield client


@pytest_asyncio.fixture(scope="session")
async def async_client():
    """Async test client for concurrent tests."""
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def admin_token():
    """Generate a valid JWT token for the demo admin user."""
    return create_access_token({"sub": "admin@upi.ai", "user_id": str(uuid.uuid4())})


@pytest.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def valid_transaction():
    return {
        "transaction_id": f"TXN-TEST-{uuid.uuid4().hex[:8].upper()}",
        "sender_vpa": "testuser123456@okicici",
        "receiver_vpa": "merchant@ybl",
        "amount": 5000.0,
        "device_id": "DEV-TEST-ABCDEF123456",
        "device_os": "Android",
        "ip_address": "192.168.1.100",
        "city": "Mumbai",
        "state": "Maharashtra",
        "is_festival_day": False,
    }


@pytest.fixture
def fraud_transaction():
    return {
        "transaction_id": f"TXN-FRAUD-{uuid.uuid4().hex[:8].upper()}",
        "sender_vpa": "victim999@okicici",
        "receiver_vpa": "mule0001@paytm",
        "amount": 49999.0,
        "device_id": f"NEW-DEV-{uuid.uuid4().hex[:8].upper()}",
        "device_os": "Android",
        "ip_address": "10.0.0.1",
        "city": "Unknown",
        "state": "Unknown",
        "is_festival_day": False,
    }


@pytest.fixture
def mock_inference_service():
    """Mock the inference service to avoid real ML model loading."""
    from app.schemas.schemas import PredictionResponse, SHAPFeature

    mock_result = PredictionResponse(
        transaction_id="TXN-MOCK-001",
        decision="ALLOW",
        risk_score=0.15,
        confidence=0.7,
        shap_features=[
            SHAPFeature(feature_name="amount", value=5000.0, shap_value=0.02, impact="positive"),
            SHAPFeature(feature_name="is_new_device", value=0.0, shap_value=-0.01, impact="negative"),
        ],
        rule_triggers=[],
        explanation_text="Transaction ALLOWED (15.0% risk). Pattern consistent with normal user behavior.",
        model_version="v1",
        inference_latency_ms=12.5,
        timestamp=datetime.now(timezone.utc),
    )

    mock_service = MagicMock()
    mock_service.is_ready = True
    mock_service.model_version = "v1"
    mock_service.predict = AsyncMock(return_value=mock_result)
    mock_service.initialize = AsyncMock()

    with patch("app.api.routes.predict.inference_service", mock_service):
        yield mock_service

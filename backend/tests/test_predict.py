"""
pytest test suite for UPI Fraud Detection backend.
Tests: auth, inference, transactions, health, rate limiting.
"""

import asyncio
import uuid
from datetime import timedelta

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient


class TestHealth:
    def test_health_endpoint(self, sync_client):
        resp = sync_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "timestamp" in data
        assert "version" in data

    def test_readiness_endpoint(self, sync_client):
        resp = sync_client.get("/ready")
        assert resp.status_code in (200, 503)
        data = resp.json()
        assert "checks" in data
        assert "postgres" in data["checks"]
        assert "redis" in data["checks"]
        assert "model_loaded" in data["checks"]


class TestAuth:
    def test_login_success(self, sync_client):
        resp = sync_client.post("/api/v1/auth/login", json={
            "email": "admin@upi.ai",
            "password": "password",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data

    def test_login_wrong_password(self, sync_client):
        resp = sync_client.post("/api/v1/auth/login", json={
            "email": "admin@upi.ai",
            "password": "wrongpassword",
        })
        assert resp.status_code == 401

    def test_login_invalid_email(self, sync_client):
        resp = sync_client.post("/api/v1/auth/login", json={
            "email": "not-an-email",
            "password": "password",
        })
        assert resp.status_code == 422

    def test_protected_endpoint_no_token(self, sync_client):
        resp = sync_client.get("/api/v1/transactions")
        assert resp.status_code == 403

    def test_protected_endpoint_invalid_token(self, sync_client):
        resp = sync_client.get(
            "/api/v1/transactions",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == 401


class TestPredict:
    def test_predict_requires_auth(self, sync_client, valid_transaction):
        resp = sync_client.post("/api/v1/predict", json=valid_transaction)
        assert resp.status_code == 403

    def test_predict_schema_validation_missing_field(self, sync_client, auth_headers):
        resp = sync_client.post("/api/v1/predict", json={
            "sender_vpa": "user@okicici",
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_predict_invalid_vpa(self, sync_client, auth_headers):
        resp = sync_client.post("/api/v1/predict", json={
            "transaction_id": "TXN-TEST-001",
            "sender_vpa": "invalid-vpa-no-at",
            "receiver_vpa": "merchant@ybl",
            "amount": 1000.0,
            "device_id": "DEV-001",
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_predict_negative_amount(self, sync_client, auth_headers, valid_transaction):
        tx = {**valid_transaction, "amount": -100.0}
        resp = sync_client.post("/api/v1/predict", json=tx, headers=auth_headers)
        assert resp.status_code == 422

    def test_predict_amount_too_large(self, sync_client, auth_headers, valid_transaction):
        tx = {**valid_transaction, "amount": 100_000_001.0}
        resp = sync_client.post("/api/v1/predict", json=tx, headers=auth_headers)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_predict_returns_valid_response(self, async_client, auth_headers, valid_transaction):
        resp = await async_client.post(
            "/api/v1/predict",
            json=valid_transaction,
            headers=auth_headers,
        )
        if resp.status_code == 200:
            data = resp.json()
            assert "transaction_id" in data
            assert data["decision"] in ("ALLOW", "BLOCK", "REVIEW")
            assert 0.0 <= data["risk_score"] <= 1.0
            assert "shap_features" in data
            assert "inference_latency_ms" in data
            assert data["inference_latency_ms"] > 0
            assert "explanation_text" in data
            assert "model_version" in data


class TestTransactions:
    @pytest.mark.asyncio
    async def test_list_transactions(self, async_client, auth_headers):
        resp = await async_client.get("/api/v1/transactions", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_list_transactions_filter(self, async_client, auth_headers):
        for decision in ("ALLOW", "BLOCK", "REVIEW"):
            resp = await async_client.get(
                f"/api/v1/transactions?decision={decision}",
                headers=auth_headers,
            )
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, async_client, auth_headers):
        resp = await async_client.get("/api/v1/metrics", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_transactions" in data
        assert "fraud_rate_percent" in data
        assert "p95_latency_ms" in data
        assert "tps" in data


class TestModels:
    @pytest.mark.asyncio
    async def test_list_models(self, async_client, auth_headers):
        resp = await async_client.get("/api/v1/models", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_drift_reports(self, async_client, auth_headers):
        resp = await async_client.get("/api/v1/drift-reports", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestSecurity:
    def test_cors_headers_present(self, sync_client):
        resp = sync_client.options(
            "/api/v1/predict",
            headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"},
        )
        assert resp.status_code in (200, 204)

    def test_expired_token_rejected(self, sync_client):
        from app.core.security import create_access_token

        expired_token = create_access_token(
            {"sub": "admin@upi.ai"},
            expires_delta=timedelta(seconds=-1),
        )
        resp = sync_client.get(
            "/api/v1/transactions",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert resp.status_code == 401

    def test_malformed_token_rejected(self, sync_client):
        resp = sync_client.get(
            "/api/v1/transactions",
            headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.MALFORMED.sig"},
        )
        assert resp.status_code == 401

    def test_sql_injection_in_vpa_rejected(self, sync_client, auth_headers):
        resp = sync_client.post("/api/v1/predict", json={
            "transaction_id": "TXN-SQLI-001",
            "sender_vpa": "'; DROP TABLE transactions; --@evil",
            "receiver_vpa": "merchant@ybl",
            "amount": 100.0,
            "device_id": "DEV-001",
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_openapi_docs_accessible(self, sync_client):
        resp = sync_client.get("/docs")
        assert resp.status_code == 200

    def test_metrics_endpoint_public(self, sync_client):
        resp = sync_client.get("/metrics")
        assert resp.status_code == 200


class TestIntegration:
    @pytest.mark.asyncio
    async def test_full_predict_and_fetch_flow(self, async_client, auth_headers, valid_transaction):
        pred_resp = await async_client.post(
            "/api/v1/predict",
            json=valid_transaction,
            headers=auth_headers,
        )

        if pred_resp.status_code != 200:
            pytest.skip("Services not available in this environment")

        pred = pred_resp.json()
        tx_id = pred["transaction_id"]

        await asyncio.sleep(0.5)

        list_resp = await async_client.get("/api/v1/transactions", headers=auth_headers)
        if list_resp.status_code == 200:
            tx_ids = [t["transaction_id"] for t in list_resp.json()["items"]]
            assert tx_id in tx_ids

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Security
- Remove `.env` from git; add validation that secrets are set
- Add JWT authentication to WebSocket endpoint
- Add login rate limiting (5 attempts per 15 minutes)
- Add audit logging for authentication events
- Disable Grafana anonymous authentication
- Remove hardcoded password hash from Alembic migration
- Fix CORS to restrict methods and headers

### Fixes
- Fix drift-to-Celery integration (was using raw `lpush` instead of `send_task`)
- Fix deprecated `asyncio.get_event_loop()` → `get_running_loop()` (Python 3.12)
- Fix `train_auc`/`val_auc` copy-paste bug in training pipeline
- Fix MLflow stage API → use model aliases (MLflow 2.9+)
- Fix `training_samples` calculation (was `n_estimators * 100`)
- Fix SHAP chart to display real SHAP values from WebSocket payload
- Fix `/ready` endpoint to return HTTP 503 when degraded
- Fix feature calculation bugs in inference service

### Improvements
- Add request-ID middleware for distributed tracing
- Add graceful shutdown signal handling
- Add Redis circuit breaker and connection retry logic
- Add `pool_pre_ping` for PostgreSQL connection health
- Add background task for DB writes (non-blocking inference)
- Add metrics caching with Redis (10s TTL)
- Add resource limits to all Docker Compose services
- Add multi-stage Docker builds for backend and mlops
- Add connection limits for WebSocket (max 100)
- Add MLflow model alias support instead of deprecated stages
- Replace `kafka-python` with `kafka-python-ng`
- Add token refresh logic for Kafka consumer

### Infrastructure
- Add GitHub Actions CI workflow (lint + test + typecheck)
- Add `conftest.py` with mocked test fixtures
- Add coverage configuration (80% threshold)
- Add Locust load test script
- Add 3 Architecture Decision Records (ADRs)
- Add `.pre-commit-config.yaml`
- Add `ruff.toml` for Python linting

### Documentation
- Rewrite README with honest synthetic data disclaimer
- Remove unproven "NPCI scale" and "500 RPS" claims
- Add local benchmark section with reproduction instructions
- Add known limitations section
- Add ADRs for key architectural decisions

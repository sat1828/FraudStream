<div align="center">

<!-- HERO BANNER — animated SVG embedded inline, renders on GitHub -->
<img src="/hero.svg" alt="FraudStream — Real-Time UPI Fraud Detection · End-to-End MLOps" width="900"/>

<br/>
<br/>

[![Python 53.4%](https://img.shields.io/badge/Python-53.4%25-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![TypeScript 37.8%](https://img.shields.io/badge/TypeScript-37.8%25-3178c6?style=flat-square&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![FastAPI 0.115](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js 15](https://img.shields.io/badge/Next.js-15-000000?style=flat-square&logo=next.js&logoColor=white)](https://nextjs.org)
[![XGBoost 2.1](https://img.shields.io/badge/XGBoost-2.1-f37626?style=flat-square)](https://xgboost.readthedocs.io)
[![MLflow 2.17](https://img.shields.io/badge/MLflow-2.17-0194e2?style=flat-square&logo=mlflow&logoColor=white)](https://mlflow.org)
[![Redpanda](https://img.shields.io/badge/Redpanda-Kafka--compatible-e7352c?style=flat-square)](https://redpanda.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ed?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![Evidently AI](https://img.shields.io/badge/Evidently-AI-ff6b35?style=flat-square)](https://evidentlyai.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)

<br/>

**One command. Fifteen services. A complete fraud-detection pipeline that generates 100K synthetic UPI transactions, trains an XGBoost classifier, streams live at 20 TPS, detects concept drift every 500 transactions, retrains itself automatically, and visualises everything in a real-time Next.js dashboard — all on your laptop.**

<br/>

> ⚠️ **Honest scope:** Synthetic data only. Local machine. Portfolio demonstration. Not connected to any real payment network. All benchmark numbers are from a MacBook Pro M2 — not production hardware.

<br/>

[Quick Start](#-quick-start) · [Architecture](#-architecture) · [ML Pipeline](#-ml-pipeline) · [Dashboard Screens](#-dashboard-screens) · [API Reference](#-api-reference) · [Design Decisions](#-design-decisions) · [Benchmarks](#-benchmarks) · [Testing](#-testing)

</div>

---

## What this is

A locally-runnable MLOps demo scoped around the Indian UPI payment network. It generates synthetic data in two phases — normal fraud mix (80K) then deep-fake VPA attacks (20K) to simulate concept drift — trains an XGBoost classifier with SHAP explainability, scores every transaction in under 80ms, monitors feature distributions with Evidently AI, and fires a Celery retraining task the moment drift exceeds 10%. The dashboard refreshes live over WebSocket, shows per-decision SHAP waterfall charts, and lets you promote or roll back model versions in one click.

**Languages:** Python 53.4% · TypeScript 37.8% · CSS 4.8% · Makefile 1.4% · Dockerfile 1.0% · Shell 0.7%

---

## 🚀 Quick Start

**Requirements:** Docker Desktop ≥ 24.0 with Compose v2 · 16 GB RAM (12 GB minimum) · 20 GB free disk

```bash
git clone https://github.com/sat1828/FraudStream.git
cd FraudStream

cp .env.example .env          # defaults work out-of-the-box for local dev

docker compose up --build     # first run: ~5-10 min  |  subsequent: ~60 s
```

Then open **http://localhost:3000** → login with `admin@upi.ai` / `password`

### Startup sequence

<img src="/startup.svg" alt="FraudStream startup sequence — animated terminal log showing all 15 services coming online in order" width="900"/>

### Makefile shortcuts

```bash
make up           # docker compose up --build
make down         # stop, keep volumes
make reset        # full wipe — stop + delete volumes
make test         # pytest suite inside Docker
make predict      # fire one test transaction, pretty-print JSON response
make health       # curl /health + /ready
make logs-backend # tail FastAPI logs only
make train        # manually trigger model retraining
make grafana      # open Grafana in browser
make lint         # ruff check + eslint
make fmt          # ruff format --fix
make ci           # lint + test + type-check (full CI chain)
```

### Service URLs

| Service | URL | Credentials |
|---|---|---|
| Dashboard | http://localhost:3000 | `admin@upi.ai` / `password` |
| API — Swagger | http://localhost:8000/docs | JWT from login |
| API — ReDoc | http://localhost:8000/redoc | — |
| MLflow | http://localhost:5000 | no auth |
| Grafana | http://localhost:3001 | `admin` / `admin` |
| Prometheus | http://localhost:9090 | no auth |
| Redpanda Console | http://localhost:18082 | no auth |

---

## 🏗 Architecture

<img src="/architecture.svg" alt="FraudStream system architecture — 15 Docker services spanning ingestion, inference, MLOps, and dashboard zones with animated flow arrows" width="900"/>

### The 15 Docker services

<img src="/services.svg" alt="FraudStream — all 15 Docker services with image names, roles, and memory limits" width="900"/>

---

## 🧠 ML Pipeline

<img src="/ml_pipeline.svg" alt="FraudStream ML pipeline — train row, serve row, and drift detection loop with animated flow arrows showing the full cycle" width="900"/>

### 1. Data generation — `mlops/producer/generate_training_data.py`

Two-phase synthetic dataset:

- **Phase 1 (80 K):** Normal fraud mix — mule rings, account-takeover bursts, velocity attacks
- **Phase 2 (20 K):** Concept drift — deep-fake VPA attacks replace the mule ring pattern

Output: `data/train.parquet`, `data/test.parquet`, `data/full_dataset.parquet`

### 2. Feature engineering — 20 features across 6 categories

<img src="/features.svg" alt="FraudStream — 20 engineered features across 6 categories: transaction, velocity, graph, device, context, temporal" width="900"/>

### 3. Training — `mlops/training/train.py`

- XGBoost 2.1 with `scale_pos_weight=40` for class imbalance
- Early stopping on validation AUC (`n_estimators=1000`, `early_stopping_rounds=50`)
- SHAP TreeExplainer on 500-sample background dataset
- All metrics, params, plots, and model artifacts logged to MLflow
- Auto-promotion to Production alias if AUC > 0.90

### 4. Feast feature store — `mlops/feast_repo/`

- **Online store:** Redis — direct key lookups ≈ 0.5 ms (bypasses Feast SDK at inference for speed)
- **Offline store:** Parquet — point-in-time correct joins for training
- **On-demand features:** `is_high_value`, `is_round_amount`, `is_just_under` — computed at request time, zero DB lookup

### 5. Inference path — `backend/app/services/inference.py`

```
Request arrives
    │
    ├── Pull 20 velocity features from Redis         ≈ 5 ms
    ├── XGBoost.predict_proba() in thread pool      ≈ 20 ms
    ├── SHAP TreeExplainer in thread pool           ≈ 10 ms
    └── Hybrid rule engine (NEW_DEVICE etc.)         ≈  1 ms
                                                    ──────
                                             total  ≈ 36 ms p50

Decision thresholds (from .env.example):
    BLOCK  ≥ MODEL_FRAUD_THRESHOLD   = 0.50
    REVIEW ≥ MODEL_REVIEW_THRESHOLD  = 0.30
    ALLOW  < MODEL_REVIEW_THRESHOLD  = 0.30
```

### 6. Inference latency breakdown

<img src="/latency.svg" alt="Inference latency breakdown — Redis 5ms, XGBoost 20ms, SHAP 10ms, rule engine 1ms, total p50 36ms vs 80ms target" width="900"/>

### 7. Drift detection & auto-retrain — `mlops/monitoring/drift_monitor.py`

Every 500 transactions (`DRIFT_DETECTION_WINDOW=500`):

1. Evidently `DataDriftPreset` compares last 500 transactions against training reference
2. Drift score = drifted features ÷ total features
3. Score > `DRIFT_THRESHOLD=0.10` → Redis alert → Celery `retrain` task queued
4. Celery worker runs `train.py` → MLflow logs new version → auto-promotes if AUC improves
5. Backend hot-reloads new model from Redis key
6. Dashboard shows red alert banner + drift score chart + confetti on completion

At 20 TPS, worst-case drift exposure window = **25 seconds** before detection fires.

---

## 🖥 Dashboard Screens

### Login

The entrypoint. JWT HS256 auth, rate-limited to 5 attempts per 15 minutes (`LOGIN_RATE_LIMIT_ATTEMPTS=5`, `LOGIN_RATE_LIMIT_WINDOW=900`). Live system-health pill shows all 15 services healthy before you log in.

### `/dashboard` — Fraud Operations Center

Eight live KPI cards polled every 5 seconds from `GET /api/v1/metrics`:

| Card | What it shows |
|---|---|
| Total transactions | Running counter since boot |
| Fraud rate | Blocked ÷ total, compared to baseline |
| Flagged today | BLOCK + REVIEW decisions in the last 24 h |
| P95 latency | Rolling 95th-percentile inference time |
| Current TPS | Live transaction rate with sparkline |
| Active model | Version, algorithm, AUC |
| Drift score | Current Evidently score vs 10% threshold |
| Last retrain | Time since last Celery retraining run |

Below: WebSocket live transaction feed (rows flash in as they arrive), SHAP waterfall panel updating per-transaction, red drift alert banner when score > 10%, Grafana latency iframe embed.

### `/dashboard/transactions` — Transaction Log

Paginated table of every scored transaction. Filter by ALL / BLOCK / ALLOW / REVIEW. Risk score as colour-coded progress bar. Click any row to expand: full SHAP breakdown, rule triggers, per-step latency breakdown (Redis / XGBoost / SHAP / Rules), decision threshold context.

### `/dashboard/network` — Threat Network

50 transaction nodes in a React Three Fiber physics simulation. Fraud nodes pulse red with a glow ring. Mule accounts cluster via edge density. Hover for label, account type, transaction count, total amount. REGENERATE button refreshes the graph. Drag to orbit, scroll to zoom.

### `/dashboard/models` — Model Registry

All trained versions from MLflow. Each card: AUC, F1, FPR, training timestamp, `DRIFT-TRIGGERED` badge when produced by the auto-retrain flow. Promote any archived version to Production or roll back the current one. OPEN MLFLOW link deeplinks to the experiment.

### `/dashboard/monitoring` — Drift Monitor

Timeline chart across all 500-transaction windows with colour-coded dots (green / amber / red). Click any drifted dot to expand: which features drifted, by what percentage, and the retrain event it triggered.

---

## 📡 API Reference

### Authentication

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@upi.ai","password":"password"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

### Fraud prediction

```bash
curl -X POST http://localhost:8000/api/v1/predict \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "TXN-001",
    "sender_vpa":     "mule0024@paytm",
    "receiver_vpa":   "victim@okicici",
    "amount":         49999.0,
    "device_id":      "NEW-DEVICE-XYZ",
    "city":           "Mumbai",
    "is_festival_day": false
  }'
```

**Response:**

```json
{
  "transaction_id":   "TXN-001",
  "decision":         "BLOCK",
  "risk_score":       0.89,
  "confidence":       0.78,
  "shap_features": [
    { "feature_name": "amount_vel_5min", "value": 49999.0,
      "shap_value": 0.42, "impact": "positive" }
  ],
  "rule_triggers":    ["NEW_DEVICE_HIGH_AMOUNT", "VELOCITY_BREACH"],
  "explanation_text": "Transaction BLOCKED — 89% fraud risk. Primary driver: high-velocity amount from new device.",
  "model_version":    "v3",
  "inference_latency_ms": 34.2
}
```

### All endpoints

```bash
GET  /health                     # liveness probe — no auth
GET  /ready                      # readiness — checks postgres, redis, model_loaded
GET  /metrics                    # Prometheus scrape target

GET  /api/v1/metrics             # KPI dashboard data (10 s Redis cache)
GET  /api/v1/transactions        # paginated log — ?page=1&page_size=20&decision=BLOCK
GET  /api/v1/models              # MLflow model versions
POST /api/v1/models/{id}/promote # promote to Production (superuser only)
GET  /api/v1/drift-reports       # all Evidently reports

WS   /ws/live                    # real-time transaction stream
```

### WebSocket events

```typescript
const ws = new WebSocket('ws://localhost:8000/ws/live')
ws.onmessage = (e) => {
  const msg = JSON.parse(e.data)
  // msg.event_type:
  //   "connected"     — initial handshake
  //   "transaction"   — new scored transaction
  //   "drift_alert"   — drift threshold exceeded
  //   "model_updated" — new model version loaded
}
```

---

## 🔬 Design Decisions

### 1. Redis direct over Feast SDK at inference

Feast's Redis online store adds ≈ 5 ms for serialisation overhead. Direct Redis key lookups for velocity counters cost ≈ 0.5 ms. With an 80 ms p95 target, that 4.5 ms matters. Feast definitions still exist for offline training joins and documentation — only the inference hot path bypasses the SDK.

**Trade-off:** Loses Feast's point-in-time correctness guarantees at serving time. Acceptable because velocity features are inherently approximate — sliding windows don't need sub-millisecond consistency.

### 2. XGBoost over neural networks

Three constraints ruled out deep learning: 100 K training records (too few for reliable neural generalisation), a sub-80 ms latency requirement, and the need for per-decision explanations under regulatory scrutiny. XGBoost + SHAP TreeExplainer satisfies all three.

**Trade-off:** Can't capture long-range temporal patterns the way an LSTM could. Mitigated by 20 hand-engineered features with rolling windows at 5-min, 1-hour, and 24-hour granularity.

### 3. Batch drift detection every 500 transactions

Online drift detectors (ADWIN, Page-Hinkley) have elevated false-positive rates at small window sizes. 500-transaction batches provide statistical significance at p < 0.05. At 20 TPS, worst-case drift exposure before detection = 25 seconds — acceptable for a demo.

**Trade-off:** Up to 500 transactions may be scored with a drifted model. Production would use shorter windows or parallel online detectors.

### 4. Monorepo with docker-compose

Single repo for local development and portfolio demonstration. Each service is independently containerised and maps cleanly to Kubernetes workloads.

**Migration path:** `docker-compose → Helm charts → ArgoCD`. Jobs for data-generator / model-trainer, Deployments for backend / frontend / celery, StatefulSets for postgres / redis / redpanda.

---

## 📊 Benchmarks

Measured on MacBook Pro M2 (8-core, 16 GB RAM), 2 uvicorn workers:

| Metric | Target | Measured | Condition |
|---|---|---|---|
| P50 inference latency | < 50 ms | ~18 ms | Redis cache hit |
| P95 inference latency | < 80 ms | 42 ms | Redis cache hit |
| P99 inference latency | < 150 ms | 89 ms | includes cold start |
| Model AUC (test set) | > 0.90 | 0.963 | synthetic data only |
| Drift detection window | ≤ 500 txns | 500 txns | configurable |
| Retraining time | < 5 min | ~3 min | 100 K records, single node |

**To reproduce:**
```bash
make up-d    # start in background
make health  # wait for ready
locust -f tests/load_test.py --headless -u 50 -r 10 --run-time 60s
```

All numbers are local measurements on a single developer machine. Not production benchmarks.

---

## 🧪 Testing

```bash
# Full pytest suite (runs inside Docker — no local Python needed)
docker compose run --rm backend pytest tests/ -v

# Or locally with Postgres + Redis running:
cd backend
pip install -r requirements.txt
pytest tests/ -v --cov=app --cov-report=html --cov-fail-under=80

# Frontend type check
cd frontend && npm run type-check

# Load test
locust -f tests/load_test.py --headless -u 50 -r 10 --run-time 60s
```

**Test categories:** `TestHealth` · `TestAuth` · `TestPredict` · `TestTransactions` · `TestModels` · `TestSecurity` (CORS, SQL injection, malformed tokens) · `TestIntegration` (predict → DB → fetch round-trip)

**Coverage threshold:** 80% (enforced in CI via `--cov-fail-under=80`)

---

## 🛠 Development Workflow

```bash
# Run only infra, develop backend locally with hot reload
docker compose up postgres redis mlflow -d
cd backend && uvicorn app.main:app --reload

# Frontend hot reload
cd frontend && npm install --legacy-peer-deps && npm run dev

# Apply a DB migration
cd backend && alembic upgrade head

# Create a new migration after changing SQLAlchemy models
cd backend && alembic revision --autogenerate -m "add_column_name"

# Full pre-commit check
pre-commit run --all-files
```

---

## 📁 Project Structure

```
FraudStream/
├── backend/
│   ├── app/
│   │   ├── api/routes/         predict.py · auth.py · transactions.py
│   │   │                       models.py · health.py
│   │   ├── core/               config · db · redis · security (JWT HS256)
│   │   │                       celery · websocket hub
│   │   ├── models/             SQLAlchemy ORM — Transaction, Prediction
│   │   │                       DriftReport, User
│   │   ├── schemas/            Pydantic v2 — PredictRequest, PredictResponse
│   │   │                       TransactionOut
│   │   └── services/
│   │       └── inference.py    XGBoost + SHAP + rules + Redis velocity
│   ├── alembic/                DB migrations
│   ├── tests/                  pytest — health · auth · predict · transactions
│   │                           models · security · integration
│   └── entrypoint.sh           wait-for-deps → alembic upgrade → seed admin → uvicorn
│
├── mlops/
│   ├── producer/
│   │   ├── generate_training_data.py   two-phase synthetic data (drift injection)
│   │   ├── transaction_producer.py     Kafka producer at 20 TPS
│   │   └── kafka_consumer.py           Redpanda → POST /predict
│   ├── training/
│   │   └── train.py            XGBoost + early stopping + SHAP + MLflow + promote
│   ├── monitoring/
│   │   └── drift_monitor.py    Evidently every 500 txns → Celery retrain trigger
│   └── feast_repo/feature_repo/
│       ├── features.py         FeatureView definitions
│       └── data_sources.py     FileSource (offline) + RedisOnlineStore (online)
│
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── dashboard/      KPIs · live feed · SHAP panel · Grafana embed
│       │   ├── transactions/   paginated log · decision filter · risk bars
│       │   ├── network/        3D force-directed fraud graph (R3F)
│       │   ├── models/         MLflow registry — promote / rollback
│       │   └── monitoring/     Evidently drift timeline + per-report detail
│       ├── components/
│       │   ├── MetricCard.tsx  animated KPI card with sparkline
│       │   ├── LiveFeed.tsx    WebSocket subscriber → transaction rows
│       │   ├── ShapChart.tsx   waterfall chart — feature contribution
│       │   └── FraudGraph.tsx  R3F physics scene — nodes, edges, labels
│       └── lib/
│           ├── api.ts          typed fetch wrapper — all backend endpoints
│           └── auth.ts         Zustand store — JWT, login, logout
│
├── docker/
│   ├── backend/Dockerfile      Python 3.12-slim · multi-stage build
│   ├── mlops/Dockerfile        Python 3.12-slim · shared ML deps
│   ├── frontend/Dockerfile     node:20-alpine · next build · standalone
│   ├── mlflow/Dockerfile       Python 3.11 · mlflow[extras] · psycopg2
│   ├── postgres/init.sql       extensions + initial schema
│   ├── prometheus/             prometheus.yml — scrape backend:8000/metrics
│   └── grafana/                provisioned datasource + pre-built dashboard JSON
│
├── tests/
│   └── load_test.py            Locust — 50 users, 10 ramp, 60 s
│
├── docs/adr/                   3 Architecture Decision Records
├── .pre-commit-config.yaml     ruff check + ruff format + type-check hooks
├── ruff.toml                   lint config — E, F, I, UP, S rule sets
├── docker-compose.yml          15-service orchestration, health checks, resource limits
├── Makefile                    developer shortcuts
├── GUIDE.md                    765-line complete operator's manual
├── CHANGELOG.md                unreleased fixes, improvements, infrastructure
└── .env.example                all configurable variables with safe defaults
```

---

## ⚙️ Environment Variables

Copy `.env.example` → `.env`. All variables have safe local-dev defaults.

| Variable | Default | Notes |
|---|---|---|
| `SECRET_KEY` | `local-dev-key` | Change for any non-local deployment |
| `POSTGRES_PASSWORD` | `upi_local_dev_2026` | |
| `ADMIN_EMAIL` | `admin@upi.ai` | Dashboard login |
| `ADMIN_PASSWORD` | `password` | Change immediately |
| `MODEL_FRAUD_THRESHOLD` | `0.5` | risk ≥ this → BLOCK |
| `MODEL_REVIEW_THRESHOLD` | `0.3` | risk ≥ this → REVIEW |
| `DRIFT_THRESHOLD` | `0.1` | 10% feature drift triggers retrain |
| `DRIFT_DETECTION_WINDOW` | `500` | Transactions per Evidently evaluation |
| `INFERENCE_TIMEOUT_MS` | `80` | Request timeout budget |
| `RATE_LIMIT_REQUESTS` | `1000` | Requests per minute per user |
| `LOGIN_RATE_LIMIT_ATTEMPTS` | `5` | Max login attempts |
| `LOGIN_RATE_LIMIT_WINDOW` | `900` | Window in seconds (15 min) |
| `KAFKA_BOOTSTRAP_SERVERS` | `redpanda:9092` | |
| `MLFLOW_MODEL_NAME` | `upi-fraud-xgboost` | |

---

## ⚠️ Known Limitations

- **Synthetic data only** — Never tested on real UPI transactions or real fraud patterns from NPCI's network
- **Single-node** — Everything runs on one machine; no horizontal scaling tested or measured
- **Simplified auth** — JWT HS256, no refresh tokens, no token revocation endpoint
- **No TLS** — All service communication is HTTP/WebSocket — local dev only
- **WebSocket unauthenticated** — Anyone on the same network can subscribe to the live feed (tracked in CHANGELOG)
- **No PII handling** — Transactions stored indefinitely, no anonymisation or retention policy
- **Benchmark numbers** — Measured on a single dev machine, not production hardware

---

## 🚢 Deployment

Designed for local demo. For a public URL:

**Railway.app** — Connect the GitHub repo, add PostgreSQL and Redis from the marketplace, copy env vars from `.env.example`, push. Railway reads `docker-compose.yml`.

**Render.com** — Web Service per component, managed Postgres + Redis addons.

**VPS (DigitalOcean / Hetzner)** — Install Docker, `git clone`, fill `.env`, `docker compose up -d`. Add nginx for TLS termination.

Full deployment walkthrough: [GUIDE.md §13](GUIDE.md)

---

## 📋 Changelog highlights

From `CHANGELOG.md [Unreleased]`:

- Fix drift-to-Celery integration (was using raw `lpush` instead of `send_task`)
- Fix deprecated `asyncio.get_event_loop()` → `get_running_loop()` (Python 3.12)
- Fix `train_auc`/`val_auc` copy-paste bug in training pipeline
- Fix MLflow stage API → use model aliases (MLflow 2.9+)
- Fix SHAP chart to display real SHAP values from WebSocket payload
- Add Redis circuit breaker and connection retry logic
- Add background task for DB writes (non-blocking inference)
- Add metrics caching with Redis (10 s TTL)
- Add resource limits to all Docker Compose services
- Add multi-stage Docker builds for backend and mlops
- Add GitHub Actions CI workflow (lint + test + typecheck)
- Add 3 Architecture Decision Records

---

<div align="center">

Built with intent for the Indian fintech ecosystem.
MIT licensed — take it, break it, make it better.

<br/>

**[⭐ Star this repo](https://github.com/sat1828/FraudStream)** if it saved you hours of "how do I wire MLflow to Celery to a WebSocket again"

</div>

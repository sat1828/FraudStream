# 🛡️ UPI Fraud MLOps Pro — Complete Operator's Guide

> **Everything you need** to run, develop, test, debug, and deploy this system.
> Written for both complete beginners and senior engineers.

---

## Table of Contents

1. [What This Project Does](#1-what-this-project-does)
2. [System Requirements](#2-system-requirements)
3. [First-Time Setup](#3-first-time-setup)
4. [Launch & Verify](#4-launch--verify)
5. [Service URLs & Credentials](#5-service-urls--credentials)
6. [The Live Demo Flow (What Happens After Startup)](#6-the-live-demo-flow)
7. [Using the Dashboard](#7-using-the-dashboard)
8. [API Reference](#8-api-reference)
9. [Understanding the ML Pipeline](#9-understanding-the-ml-pipeline)
10. [Development Workflow](#10-development-workflow)
11. [Running Tests](#11-running-tests)
12. [Stopping & Resetting](#12-stopping--resetting)
13. [Deployment (Railway / Render)](#13-deployment)
14. [Troubleshooting](#14-troubleshooting)
15. [Architecture Deep-Dive](#15-architecture-deep-dive)
16. [Security Hardening for Production](#16-security-hardening)

---

## 1. What This Project Does

This is a **production-grade, real-time UPI fraud detection system** that:

- 🔴 **Detects fraud in < 80ms** using XGBoost + 20 Feast features from Redis
- 🧠 **Explains every decision** with SHAP waterfall charts per transaction
- 📊 **Monitors model health** with Evidently AI drift detection every 500 transactions
- 🔄 **Auto-retrains** via Celery when concept drift is detected
- 📡 **Streams live data** to a glassmorphic Next.js 16 dashboard via WebSockets
- 🕸️ **Visualises fraud rings** in a physics-simulated 3D force-directed graph
- 📈 **Tracks everything** with Prometheus metrics + pre-built Grafana dashboards

**Tech stack:** FastAPI · Next.js 16 · XGBoost · SHAP · MLflow · Feast · Evidently · Redpanda (Kafka) · Redis · PostgreSQL · Celery · Prometheus · Grafana · Docker

---

## 2. System Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM | 12 GB | 16 GB |
| CPU | 4 cores | 8 cores |
| Disk | 10 GB free | 20 GB free |
| Docker | 24.0+ | 25.0+ |
| Docker Compose | v2.20+ | v2.24+ |
| OS | macOS 13, Ubuntu 22, Windows 11 (WSL2) | macOS 14 / Ubuntu 24 |

**Check your versions:**
```bash
docker --version          # Docker version 24.x+
docker compose version    # Docker Compose version v2.x
```

---

## 3. First-Time Setup

### Step 1 — Clone / Unzip

```bash
# If cloning from GitHub:
git clone https://github.com/yourusername/upi-fraud-mlops-pro.git
cd upi-fraud-mlops-pro

# If you have the ZIP:
unzip upi-fraud-mlops-pro.zip
cd upi-fraud-mlops-pro
```

### Step 2 — Configure Environment

```bash
# The project ships with a ready .env for local dev (already inside the zip)
# Just verify it exists:
cat .env
```

You should see:
```
SECRET_KEY=local-dev-secret-key-not-for-production-replace-me
POSTGRES_PASSWORD=upi_local_dev_2026
ADMIN_EMAIL=admin@upi.ai
ADMIN_PASSWORD=password
...
```

> **For production**, copy `.env.example` to `.env` and set strong secrets:
> ```bash
> cp .env.example .env
> # Edit .env — fill in SECRET_KEY (openssl rand -hex 32), POSTGRES_PASSWORD, etc.
> ```

### Step 3 — That's it! No other setup needed.

All dependencies are inside Docker. No Python/Node.js installation required on your host machine.

---

## 4. Launch & Verify

### The ONE command:

```bash
docker-compose up --build
```

> First run downloads ~3 GB of Docker images and builds all services. Takes **5–10 minutes** once. Subsequent runs take ~60 seconds.

### What to watch in logs:

```
[postgres]       database system is ready to accept connections  ← ~10s
[redis]          Ready to accept connections                      ← ~10s
[redpanda]       Successfully started Redpanda!                  ← ~15s
[mlflow]         Uvicorn running on http://0.0.0.0:5000          ← ~20s
[data-gen]       Dataset generated: 100,000 transactions         ← ~60s
[trainer]        ✅ Training complete! AUC: 0.97                  ← ~120s
[backend]        Uvicorn running on http://0.0.0.0:8000          ← ~130s
[producer]       Transaction stream started at 20 TPS            ← ~140s
[consumer]       Kafka consumer connected                         ← ~145s
[frontend]       Ready on http://0.0.0.0:3000                    ← ~150s
```

### Verify everything is healthy:

```bash
# In a new terminal tab:
docker-compose ps

# Should show all services as "Up" or "healthy":
# NAME                STATUS
# upi_postgres        Up (healthy)
# upi_redis           Up (healthy)
# upi_redpanda        Up (healthy)
# upi_mlflow          Up (healthy)
# upi_backend         Up (healthy)
# upi_frontend        Up
# upi_grafana         Up
# ...
```

Or hit the health endpoint:
```bash
curl http://localhost:8000/health
# → {"status":"ok","timestamp":"2026-..."}

curl http://localhost:8000/ready
# → {"status":"ok","checks":{"postgres":"ok","redis":"ok","model_loaded":true,...}}
```

---

## 5. Service URLs & Credentials

| Service | URL | Default Credentials |
|---------|-----|---------------------|
| 🎨 **Dashboard** | http://localhost:3000 | `admin@upi.ai` / `password` |
| 📖 **API Docs** (Swagger) | http://localhost:8000/docs | JWT token from login |
| 📖 **API Docs** (ReDoc) | http://localhost:8000/redoc | — |
| 🔬 **MLflow UI** | http://localhost:5000 | No auth |
| 📊 **Grafana** | http://localhost:3001 | `admin` / `admin` |
| 📈 **Prometheus** | http://localhost:9090 | No auth |
| 📡 **Redpanda Console** | http://localhost:18082 | No auth |
| 🗄️ **PostgreSQL** | `localhost:5432` | user:`upi_user` pw:`upi_local_dev_2026` db:`upi_fraud` |
| ⚡ **Redis** | `localhost:6379` | No auth (dev mode) |

---

## 6. The Live Demo Flow

This is what a recruiter / interviewer sees when you show the project:

### T+0 min — Open Dashboard
Navigate to http://localhost:3000 → Login with `admin@upi.ai` / `password`

### T+1 min — Live Transactions Appear
The **FRAUD OPERATIONS CENTER** shows:
- KPI cards counting up in real-time (total transactions, fraud rate, latency)
- Live transaction stream table populating row-by-row
- SHAP waterfall chart updating with every new transaction's explanation
- TPS sparkline showing real throughput

### T+2 min — Explore Threat Network
Click **THREAT MAP** in the sidebar:
- 50 nodes self-organise under physics simulation
- Fraud/mule accounts cluster together and pulse red
- Hover any node for label, type, transaction count, total amount
- Drag to rotate, scroll to zoom

### T+3 min — Watch Concept Drift Happen
After ~60 seconds of streaming, the producer **injects a new fraud pattern**
(deep-fake VPA attacks replace mule rings). Within 500 more transactions:
1. 🚨 **Red drift banner** appears at the top of dashboard
2. Drift score bar fills towards the 10% threshold
3. "Retraining model..." spinner appears
4. Celery worker retrains XGBoost on the full dataset
5. New model version registered in MLflow
6. 🎉 **Confetti** fires when retrain completes and model is promoted

### T+5 min — Explore Model Registry
Click **MODEL REGISTRY**:
- All trained versions listed with AUC, F1, FPR metrics
- "DRIFT-TRIGGERED" badge on the auto-retrained version
- Promote / Rollback buttons

### T+6 min — Check MLflow
Open http://localhost:5000 → See experiment runs, metrics plots, model artifacts, SHAP plots

### T+7 min — Check Grafana
Open http://localhost:3001 → UPI Fraud Detection dashboard pre-loaded:
- P50/P95/P99 inference latency time-series
- Request rate by status code
- Error rate panel

---

## 7. Using the Dashboard

### Overview Page (`/dashboard`)
- **8 KPI cards**: all polled live from `GET /api/v1/metrics` every 5 seconds
- **Live feed**: WebSocket stream at `ws://localhost:8000/ws/live`
- **SHAP panel**: automatically updates with the most recently processed transaction
- **Grafana embed**: embedded iframe at bottom (full dashboard at http://localhost:3001)

### Transactions Page (`/dashboard/transactions`)
- Paginated table of all scored transactions
- Filter by decision: ALL / ALLOW / BLOCK / REVIEW
- Risk score progress bars, per-row latency

### Threat Network (`/dashboard/network`)
- Physics simulation refreshes every animation frame
- Click **REGENERATE** to get a new random graph
- Fraud nodes have glow rings + point lights

### Model Registry (`/dashboard/models`)
- Promote any version to Production (requires superuser JWT)
- Rollback to previous version in one click
- Links to MLflow UI for full experiment tracking

### Drift Monitor (`/dashboard/monitoring`)
- Timeline chart of drift scores across all detection windows
- Threshold reference line at 10%
- Red dots on chart = drift events that triggered retrain
- Per-report details: drifted feature names, transaction count, retrain status

---

## 8. API Reference

### Authentication

```bash
# Get JWT token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@upi.ai","password":"password"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "Token: $TOKEN"
```

### Real-Time Fraud Prediction

```bash
curl -X POST http://localhost:8000/api/v1/predict \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "TXN-DEMO-001",
    "sender_vpa":   "victim@okicici",
    "receiver_vpa": "mule0001@paytm",
    "amount":       49999.0,
    "device_id":    "NEW-DEVICE-XYZ",
    "city":         "Mumbai",
    "is_festival_day": false
  }'
```

**Response:**
```json
{
  "transaction_id": "TXN-DEMO-001",
  "decision": "BLOCK",
  "risk_score": 0.89,
  "confidence": 0.78,
  "shap_features": [
    { "feature_name": "amount_velocity_5min", "value": 49999.0, "shap_value": 0.42, "impact": "positive" },
    ...
  ],
  "rule_triggers": ["NEW_DEVICE_HIGH_AMOUNT"],
  "explanation_text": "Transaction BLOCKED with 89.0% fraud risk...",
  "model_version": "v3",
  "inference_latency_ms": 34.2
}
```

### Other Endpoints

```bash
# System metrics (KPI cards)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/metrics

# Transaction history
curl -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/v1/transactions?page=1&page_size=20"

# Filter by decision
curl -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/v1/transactions?decision=BLOCK"

# Model versions
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/models

# Drift reports
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/drift-reports

# Health check (no auth)
curl http://localhost:8000/health
curl http://localhost:8000/ready

# Prometheus metrics (no auth)
curl http://localhost:8000/metrics
```

### WebSocket (Real-Time Stream)

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/live')
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data)
  // msg.event_type: "connected" | "transaction" | "drift_alert" | "model_updated"
  console.log(msg)
}
```

---

## 9. Understanding the ML Pipeline

### Data Generation (`mlops/producer/generate_training_data.py`)
- Generates 100,000 synthetic UPI transactions using Faker + realistic patterns
- **Phase 1 (80k txns):** Normal fraud mix — mule rings, account takeover, velocity fraud
- **Phase 2 (20k txns):** Concept drift — deep-fake VPA fraud pattern introduced
- Saves `train.parquet` + `test.parquet` + `full_dataset.parquet` to `/data/`

### Feature Engineering (20 features)
| Category | Features |
|----------|---------|
| Transaction | `amount`, `amount_log`, `amount_zscore` |
| Velocity (sender) | `txn_count_5min/1h/24h`, `amount_velocity_5min/1h/24h` |
| Graph (sender) | `sender_unique_receivers_1h`, `sender_unique_devices_24h` |
| Device | `device_txn_count_1h/24h`, `is_new_device` |
| Context | `is_new_receiver`, `receiver_txn_count_1h`, `is_night_txn`, `is_festival_day` |
| Temporal | `hour_of_day`, `day_of_week` |

### Training (`mlops/training/train.py`)
- XGBoost with `scale_pos_weight=40` for class imbalance
- Early stopping on validation AUC
- SHAP TreeExplainer computed on 500 sample rows
- All metrics, params, artifacts logged to MLflow
- Model auto-promoted to Production if AUC > 0.90

### Inference (`backend/app/services/inference.py`)
```
Request → Redis velocity counters (< 5ms)
        → XGBoost.predict_proba() (< 20ms, thread pool)
        → SHAP TreeExplainer (< 10ms)
        → Rule engine (< 1ms)
        → Response (total < 80ms p95)
```

### Drift Detection (`mlops/monitoring/drift_monitor.py`)
- Runs every 500 transactions (configurable via `DRIFT_DETECTION_WINDOW`)
- Evidently `DataDriftPreset` compares last 500 transactions vs. training reference
- Drift score = (# drifted features) / (total features)
- If score > 10% threshold: publishes Redis alert → Celery retrain task

### Feast Feature Store (`mlops/feast_repo/`)
- **Online store**: Redis — sub-10ms feature lookup
- **Offline store**: Parquet files — point-in-time correct training joins
- **On-demand features**: `is_high_value`, `is_round_amount`, `is_just_under` (computed at request time, zero DB lookup)
- Run `feast apply` to register definitions; `feast materialize-incremental` to sync offline → online

---

## 10. Development Workflow

### Backend (Python / FastAPI)

```bash
# Option 1: Run locally (requires Postgres + Redis running)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Option 2: Only start infra services, run backend locally
docker-compose up postgres redis mlflow -d
cd backend && uvicorn app.main:app --reload

# Apply DB migrations
cd backend
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "add_new_column"
```

### Frontend (Next.js)

```bash
cd frontend
npm install --legacy-peer-deps
npm run dev       # http://localhost:3000 with hot reload

# Type check
npm run type-check

# Lint
npm run lint

# Build for production
npm run build
```

### Makefile shortcuts

```bash
make up           # docker-compose up --build
make up-d         # background mode
make down         # stop all
make reset        # stop + delete all volumes (full wipe)
make logs         # tail all logs
make logs-backend # tail backend only
make test         # run pytest
make health       # curl health endpoints
make login        # get JWT token
make predict      # test predict endpoint (set TOKEN= first)
```

### Adding a new feature

1. Add feature to `mlops/feast_repo/feature_repo/features.py` schema
2. Update `FEATURE_NAMES` list in `backend/app/services/inference.py`
3. Add feature computation in `mlops/producer/generate_training_data.py`
4. Add Redis counter update in `inference.py::_update_counters()`
5. Retrain model: `docker-compose run --rm model-trainer`
6. MLflow promotes new version automatically if AUC improves

---

## 11. Running Tests

```bash
# Full test suite (requires Postgres + Redis)
cd backend
pytest tests/ -v

# Run specific test class
pytest tests/test_predict.py::TestSecurity -v
pytest tests/test_predict.py::TestPredict -v

# With coverage report
pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html

# Run inside Docker (no local Python needed)
docker-compose run --rm backend pytest tests/ -v

# CI runs automatically on every push (see .github/workflows/ci-cd.yml)
```

**Test categories:**
- `TestHealth` — health + readiness endpoints
- `TestAuth` — login, JWT validation, expired token rejection
- `TestPredict` — schema validation, latency target, concurrent requests
- `TestTransactions` — list + filter endpoints
- `TestModels` — model registry endpoints
- `TestSecurity` — CORS, SQL injection, malformed tokens
- `TestIntegration` — end-to-end predict → DB → fetch flow

---

## 12. Stopping & Resetting

```bash
# Stop all services (keep data)
docker-compose down

# Stop and DELETE all data (volumes) — full reset
docker-compose down -v

# Remove all built images too (forces full rebuild)
docker-compose down -v --rmi all

# Just restart one service
docker-compose restart backend

# Scale inference workers (if needed)
docker-compose up --scale celery-worker=3 -d
```

---

## 13. Deployment

### Railway.app (Easiest — free tier available)

1. Push your code to GitHub
2. Go to https://railway.app → New Project → Deploy from GitHub
3. Add these services: **PostgreSQL**, **Redis** (from Railway marketplace)
4. Set environment variables in Railway dashboard (copy from `.env.example`)
5. Railway auto-detects `docker-compose.yml` and deploys all services

**Required env vars for Railway:**
```
SECRET_KEY          = <openssl rand -hex 32>
POSTGRES_PASSWORD   = <from Railway Postgres addon>
ADMIN_EMAIL         = admin@yourdomain.com
ADMIN_PASSWORD      = <strong password>
POSTGRES_HOST       = <Railway Postgres hostname>
REDIS_URL           = <Railway Redis URL>
NEXT_PUBLIC_API_URL = https://your-backend.railway.app
NEXT_PUBLIC_WS_URL  = wss://your-backend.railway.app
```

### Render.com

1. Create a new **Web Service** → connect GitHub repo
2. Build command: `docker-compose build backend`
3. Start command: `docker-compose up backend`
4. Add **PostgreSQL** and **Redis** from Render marketplace
5. Set environment variables in Render dashboard

### Self-hosted VPS (DigitalOcean / Hetzner)

```bash
# On your VPS (Ubuntu 22.04):
git clone https://github.com/yourusername/upi-fraud-mlops-pro.git
cd upi-fraud-mlops-pro
cp .env.example .env
nano .env  # fill in production secrets

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Run with production compose
docker-compose up --build -d

# Add nginx reverse proxy for TLS
# (see docker/nginx/nginx.conf example in production hardening section)
```

---

## 14. Troubleshooting

### "Service is unhealthy" on startup

```bash
# Check which service is failing
docker-compose ps

# Check its logs
docker-compose logs postgres
docker-compose logs redis
docker-compose logs backend
```

**Common fixes:**
- `postgres` unhealthy: Port 5432 already in use → change `POSTGRES_EXTERNAL_PORT=5433` in `.env`
- `redis` unhealthy: Port 6379 in use → change `REDIS_EXTERNAL_PORT=6380` in `.env`
- `backend` unhealthy: Wait longer — it waits for MLflow which waits for Postgres

### "No transactions appearing in dashboard"

The stream starts only after model training completes (~2 min). Check:
```bash
docker-compose logs model-trainer | tail -20
docker-compose logs transaction-producer | tail -20
docker-compose logs kafka-consumer | tail -20
```

### "feast apply failed"

```bash
docker-compose logs feast-apply
# Common issue: Redis not ready yet
# Fix: feast-apply has retry logic built in — wait 30s and it retries
```

### "SHAP panel shows zeros"

The SHAP panel shows data from the live WebSocket. It will populate once the first transaction arrives (~3 min after startup). If it stays empty:
```bash
# Check WebSocket is working
curl -i http://localhost:8000/health
docker-compose logs backend | grep -i websocket
```

### Out of memory

Reduce memory usage by disabling some optional services:
```bash
# Minimal mode: no Grafana/Prometheus
docker-compose up --build postgres redis redpanda mlflow backend frontend
```

### Re-train model manually

```bash
docker-compose run --rm model-trainer python /app/training/train.py
```

### Reset only the ML pipeline (keep infra)

```bash
docker-compose stop model-trainer transaction-producer kafka-consumer drift-monitor
docker volume rm upi-fraud-mlops-pro_mlflow_artifacts 2>/dev/null || true
rm -f data/*.parquet
docker-compose up model-trainer transaction-producer kafka-consumer drift-monitor
```

---

## 15. Architecture Deep-Dive

```
┌─────────────────────────────────────────────────────────────────────┐
│                         INGESTION LAYER                              │
│  Transaction Producer (20 TPS synthetic)                             │
│         │                                                            │
│         ▼                                                            │
│  Redpanda (Kafka-compatible) ──► topic: upi-raw-transactions         │
│         │                                                            │
│         ▼                                                            │
│  Kafka Consumer ──► POST /api/v1/predict                             │
└─────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        INFERENCE LAYER  (< 80ms p95)                │
│                                                                      │
│  FastAPI /predict                                                    │
│    ├── Feast online store (Redis)  ← velocity features  ~5ms        │
│    ├── XGBoost predict_proba()     ← thread pool        ~20ms       │
│    ├── SHAP TreeExplainer          ← thread pool        ~10ms       │
│    └── Hybrid rule engine          ← in-memory          ~1ms        │
│                                                                      │
│  Returns: { decision, risk_score, shap_features, latency_ms }       │
└─────────────────────────────────────────────────────────────────────┘
         │
         ├──► PostgreSQL (persist transaction + prediction)
         ├──► Redis (update velocity counters, push to metrics)
         └──► WebSocket /ws/live (broadcast to dashboard)
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          FRONTEND (Next.js 16)                       │
│                                                                      │
│  /dashboard         — KPIs (real API) + live feed + SHAP chart      │
│  /transactions      — Paginated scored transaction log               │
│  /network           — 3D force-directed fraud graph (R3F)           │
│  /models            — MLflow model registry + promote/rollback       │
│  /monitoring        — Evidently drift reports + timeline chart       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                          MLOPS LAYER                                 │
│                                                                      │
│  Evidently Drift Monitor                                             │
│    ├── Runs every 500 transactions                                   │
│    ├── Compares feature distributions vs. training reference         │
│    └── Drift score > 10% → triggers Celery retrain task             │
│                                                                      │
│  Celery Worker                                                       │
│    └── Runs train.py → MLflow logs → auto-promotes model             │
│                                                                      │
│  MLflow Registry                                                     │
│    ├── Experiment tracking (metrics, params, artifacts)              │
│    └── Model versioning (Staging → Production → Archived)           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 16. Security Hardening

### Required before production deployment:

```bash
# 1. Generate strong SECRET_KEY
openssl rand -hex 32

# 2. Generate strong DB password  
openssl rand -base64 32

# 3. Set all in .env (never commit .env to git)
```

### Production .env checklist:
```
[ ] SECRET_KEY       — 64-char hex random (openssl rand -hex 32)
[ ] POSTGRES_PASSWORD — 40-char random
[ ] ADMIN_PASSWORD   — 20+ char, stored in password manager
[ ] REDIS_PASSWORD   — set for any internet-accessible Redis
[ ] GRAFANA_PASSWORD — changed from default 'admin'
```

### Additional hardening:
- **TLS**: Put nginx/Traefik in front of all services, terminate SSL there
- **Secrets Manager**: In production, pull secrets from AWS SSM, GCP Secret Manager, or HashiCorp Vault — never from `.env` files
- **CORS**: Update `CORS_ORIGINS` in `backend/app/core/config.py` to your actual frontend domain
- **Rate Limiting**: Default is 1000 req/min per user — tune `RATE_LIMIT_REQUESTS` for your traffic
- **Database**: Enable PostgreSQL SSL (`sslmode=require`), restrict pg_hba.conf
- **Network**: In Kubernetes/cloud, put services on private network — only expose ports 80/443 publicly
- **Monitoring**: Set up PagerDuty/Alertmanager alerts on Prometheus for p99 > 200ms and error rate > 1%

---

## Quick Reference Card

```bash
# Start
docker-compose up --build

# Stop  
docker-compose down

# Full reset (delete all data)
docker-compose down -v

# View logs
docker-compose logs -f backend
docker-compose logs -f drift-monitor

# Run tests
docker-compose run --rm backend pytest tests/ -v

# Get API token
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@upi.ai","password":"password"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])"

# Test prediction
curl -X POST http://localhost:8000/api/v1/predict \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"transaction_id":"T1","sender_vpa":"u@okicici","receiver_vpa":"m@ybl","amount":5000,"device_id":"DEV1","city":"Mumbai","is_festival_day":false}'

# Dashboard   → http://localhost:3000
# API Docs    → http://localhost:8000/docs  
# MLflow      → http://localhost:5000
# Grafana     → http://localhost:3001
```

---

*Built with ❤️ for the Indian fintech ecosystem. Questions? Open an issue on GitHub.*

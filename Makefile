# UPI Fraud MLOps — Developer Makefile
.PHONY: up down logs test test-cov lint fmt typecheck ci clean clean-py clean-next reset

# ─── Primary Commands ─────────────────────────────────────────────────────────

up:
	docker-compose up --build

up-d:
	docker-compose up --build -d

down:
	docker-compose down

reset:
	docker-compose down -v --remove-orphans
	docker volume prune -f

logs:
	docker-compose logs -f

logs-%:
	docker-compose logs -f $*

# ─── Development ─────────────────────────────────────────────────────────────

dev-backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

install-frontend:
	cd frontend && npm install --legacy-peer-deps

# ─── Testing ─────────────────────────────────────────────────────────────────

test:
	cd backend && python -m pytest tests/ -v --tb=short

test-cov:
	cd backend && python -m pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing

load-test:
	locust -f tests/load_test.py --headless -u 50 -r 10 --run-time 60s

typecheck:
	cd frontend && npm run type-check

# ─── Linting & Formatting ────────────────────────────────────────────────────

lint:
	cd backend && python -m ruff check app/
	cd frontend && npm run lint

fmt:
	cd backend && python -m ruff format app/
	cd backend && python -m ruff check --fix app/

ci: lint test typecheck

# ─── Data & ML ────────────────────────────────────────────────────────────────

generate-data:
	docker-compose run --rm data-generator

train:
	docker-compose run --rm model-trainer

mlflow:
	open http://localhost:5000 2>/dev/null || start http://localhost:5000

grafana:
	open http://localhost:3001 2>/dev/null || start http://localhost:3001

# ─── API Utilities ────────────────────────────────────────────────────────────

login:
	@curl -s -X POST http://localhost:8000/api/v1/auth/login \
	  -H "Content-Type: application/json" \
	  -d '{"email": "admin@upi.ai", "password": "password"}' | python3 -m json.tool

predict:
	@TOKEN=$$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
	  -H "Content-Type: application/json" \
	  -d '{"email": "admin@upi.ai", "password": "password"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])") && \
	curl -s -X POST http://localhost:8000/api/v1/predict \
	  -H "Authorization: Bearer $$TOKEN" \
	  -H "Content-Type: application/json" \
	  -d '{"transaction_id":"TXN-DEMO-001","sender_vpa":"user123@okicici","receiver_vpa":"merchant@ybl","amount":5000,"device_id":"DEV-ABC123","city":"Mumbai","is_festival_day":false}' \
	  | python3 -m json.tool

health:
	@curl -s http://localhost:8000/health | python3 -m json.tool
	@curl -s http://localhost:8000/ready | python3 -m json.tool

# ─── Cleanup ─────────────────────────────────────────────────────────────────

clean-py:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	find . -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true

clean-next:
	rm -rf frontend/.next frontend/node_modules

clean: clean-py clean-next
	docker system prune -f

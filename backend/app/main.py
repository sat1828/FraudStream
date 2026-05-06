"""
UPI Fraud Detection - FastAPI Backend
Production-grade async API with WebSocket support, JWT auth, and real-time inference.
"""

import asyncio
import logging
import signal
from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.routes import auth, health, models, predict, transactions, websocket
from app.core.config import settings
from app.core.database import engine, Base, shutdown_db
from app.core.redis_client import redis_client
from app.core.websocket_manager import manager
from app.middleware.request_id import RequestIDMiddleware

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if settings.DEBUG else structlog.processors.JSONRenderer(),
    ],
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    logger.info("Starting UPI Fraud Detection API", version=settings.VERSION)

    await redis_client.ping()
    logger.info("Redis connected")

    await manager.start_broadcast_loop()

    shutdown_event = asyncio.Event()

    def handle_signal(sig: int) -> None:
        logger.info("Received shutdown signal", signal=sig)
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, handle_signal, sig)

    yield

    logger.info("Shutting down gracefully")
    await manager.stop_broadcast_loop()
    await manager.close_all()
    await redis_client.close()
    await shutdown_db()
    logger.info("Shutdown complete")


docs_url = "/docs" if settings.OPENAPI_ENABLED else None
redoc_url = "/redoc" if settings.OPENAPI_ENABLED else None

app = FastAPI(
    title="UPI Fraud Detection API",
    description="Real-time UPI fraud detection with XGBoost, SHAP explainability, and drift detection.",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url=docs_url,
    redoc_url=redoc_url,
)

app.add_middleware(RequestIDMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    max_age=600,
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=True,
    should_respect_env_var=False,
    should_instrument_requests_inprogress=True,
    excluded_handlers=["/health", "/metrics", "/ready"],
    inprogress_labels=True,
).instrument(app).expose(app, endpoint="/metrics")

app.include_router(health.router, tags=["Health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(predict.router, prefix="/api/v1", tags=["Inference"])
app.include_router(transactions.router, prefix="/api/v1", tags=["Transactions"])
app.include_router(models.router, prefix="/api/v1", tags=["Model Registry"])
app.include_router(websocket.router, tags=["WebSocket"])

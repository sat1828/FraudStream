"""Health and readiness check endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis_client import redis_client
from app.services.inference import inference_service

router = APIRouter()


@router.get("/health", tags=["Health"])
async def health_check():
    """Shallow health check for load balancers."""
    return {
        "status": "ok",
        "version": __import__("app.core.config", fromlist=["settings"]).settings.VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/ready", tags=["Health"])
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Deep health check for Kubernetes/Docker readiness probe. Returns 503 if degraded."""
    checks = {}
    overall = True

    try:
        await db.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = f"error: {str(e)}"
        overall = False

    try:
        pong = await redis_client.ping()
        checks["redis"] = "ok" if pong else "no_pong"
        if not pong:
            overall = False
    except Exception as e:
        checks["redis"] = f"error: {str(e)}"
        overall = False

    checks["model_loaded"] = inference_service.is_ready
    checks["model_version"] = inference_service.model_version
    if not inference_service.is_ready:
        overall = False

    status_code = 200 if overall else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if overall else "degraded",
            "checks": checks,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

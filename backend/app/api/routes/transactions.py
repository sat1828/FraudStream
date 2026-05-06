"""Transaction history and metrics endpoints with caching."""

from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis_client import redis_client
from app.core.security import get_current_user
from app.models.user import Transaction, User
from app.schemas.schemas import (
    SystemMetrics,
    TransactionListResponse,
    TransactionListItem,
)

router = APIRouter()
logger = structlog.get_logger(__name__)

METRICS_CACHE_TTL = 10


@router.get("/transactions", response_model=TransactionListResponse)
async def list_transactions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, le=200),
    decision: Optional[str] = Query(default=None, description="ALLOW|BLOCK|REVIEW"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get paginated transaction history with predictions."""
    query = select(Transaction).order_by(Transaction.created_at.desc())

    if decision:
        query = query.where(Transaction.decision == decision.upper())

    count_query = select(func.count(Transaction.id))
    if decision:
        count_query = count_query.where(Transaction.decision == decision.upper())
    count_result = await db.execute(count_query)
    total = count_result.scalar_one() or 0

    paginated = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(paginated)
    transactions = result.scalars().all()

    return TransactionListResponse(
        items=[TransactionListItem.model_validate(tx) for tx in transactions],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/metrics", response_model=SystemMetrics)
async def get_system_metrics(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Real-time system metrics for dashboard KPI cards with Redis caching."""
    cached = await redis_client.get("metrics:cache")
    if cached:
        import json

        return SystemMetrics(**json.loads(cached))

    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)

    total_result = await db.execute(select(func.count(Transaction.id)))
    total = total_result.scalar_one() or 0

    hour_result = await db.execute(
        select(func.count(Transaction.id)).where(Transaction.created_at >= one_hour_ago)
    )
    last_hour = hour_result.scalar_one() or 0

    blocked_result = await db.execute(
        select(func.count(Transaction.id)).where(Transaction.decision == "BLOCK")
    )
    blocked = blocked_result.scalar_one() or 0
    fraud_rate = (blocked / max(total, 1)) * 100

    latencies = await redis_client.lrange("latency:recent", 0, 999)
    if latencies:
        lat_floats = sorted([float(l) for l in latencies if l])
        avg_lat = sum(lat_floats) / len(lat_floats)
        p95_idx = int(len(lat_floats) * 0.95)
        p95_lat = lat_floats[min(p95_idx, len(lat_floats) - 1)]
        await redis_client.delete("latency:recent")
    else:
        avg_lat, p95_lat = 0.0, 0.0

    model_version = await redis_client.get("current_model_version") or "unknown"

    drift_score_str = await redis_client.get("current_drift_score")
    drift_score = float(drift_score_str) if drift_score_str else 0.0

    last_retrain_str = await redis_client.get("last_retrain_time")
    last_retrain = (
        datetime.fromisoformat(last_retrain_str) if last_retrain_str else None
    )

    tps = last_hour / 3600 if last_hour > 0 else 0.0

    metrics = SystemMetrics(
        total_transactions=total,
        transactions_last_hour=last_hour,
        fraud_rate_percent=round(fraud_rate, 3),
        avg_latency_ms=round(avg_lat, 2),
        p95_latency_ms=round(p95_lat, 2),
        current_model_version=model_version,
        drift_score=round(drift_score, 4),
        last_retrain=last_retrain,
        tps=round(tps, 2),
    )

    import json

    await redis_client.set("metrics:cache", json.dumps(metrics.model_dump()), ttl=METRICS_CACHE_TTL)
    return metrics

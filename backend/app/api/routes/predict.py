"""Predict router - Core fraud detection endpoint."""

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.redis_client import redis_client
from app.core.security import get_current_user
from app.core.websocket_manager import manager
from app.models.user import Transaction, User
from app.schemas.schemas import PredictionResponse, TransactionRequest
from app.services.inference import inference_service

router = APIRouter()
logger = structlog.get_logger(__name__)


async def rate_limit_check(
    request: Request,
    user: User = Depends(get_current_user),
):
    """Redis-backed rate limiting: 1000 req/min per user."""
    key = f"user:{str(user.id)}"
    allowed, remaining = await redis_client.check_rate_limit(
        key, settings.RATE_LIMIT_REQUESTS, settings.RATE_LIMIT_WINDOW
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {settings.RATE_LIMIT_WINDOW}s",
            headers={
                "Retry-After": str(settings.RATE_LIMIT_WINDOW),
                "X-RateLimit-Remaining": "0",
            },
        )
    return user


async def persist_transaction(
    db: AsyncSession,
    transaction: TransactionRequest,
    result: PredictionResponse,
    feature_dict: dict,
) -> None:
    """Persist prediction result to database (background task)."""
    db_transaction = Transaction(
        transaction_id=transaction.transaction_id,
        sender_vpa=transaction.sender_vpa,
        receiver_vpa=transaction.receiver_vpa,
        amount=transaction.amount,
        device_id=transaction.device_id,
        device_os=transaction.device_os,
        ip_address=transaction.ip_address,
        city=transaction.city,
        state=transaction.state,
        is_festival_day=transaction.is_festival_day,
        festival_name=transaction.festival_name,
        features=feature_dict,
        risk_score=result.risk_score,
        decision=result.decision,
        shap_values={f.feature_name: f.shap_value for f in result.shap_features},
        rule_triggers=result.rule_triggers,
        explanation_text=result.explanation_text,
        model_version=result.model_version,
        inference_latency_ms=result.inference_latency_ms,
        initiated_at=transaction.initiated_at or datetime.now(timezone.utc),
    )
    db.add(db_transaction)
    await db.commit()


@router.post(
    "/predict",
    response_model=PredictionResponse,
    summary="Real-time fraud prediction",
    description="Run fraud detection on a UPI transaction. Returns risk score, decision, and SHAP explanation.",
)
async def predict(
    transaction: TransactionRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(rate_limit_check),
):
    """Main fraud detection endpoint."""
    request_id = getattr(request.state, "request_id", "unknown")
    log = logger.bind(
        transaction_id=transaction.transaction_id,
        sender_vpa=transaction.sender_vpa,
        amount=transaction.amount,
        request_id=request_id,
    )
    log.info("Prediction request received")

    if not inference_service.is_ready:
        await inference_service.initialize()

    try:
        result = await inference_service.predict(transaction)
    except Exception as e:
        log.error("Inference failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Inference failed. Please try again.",
        )

    feature_dict = {f.feature_name: f.value for f in result.shap_features}

    background_tasks.add_task(
        persist_transaction, db, transaction, result, feature_dict
    )

    ws_payload = {
        "event_type": "transaction",
        "payload": {
            "transaction_id": result.transaction_id,
            "sender_vpa": transaction.sender_vpa,
            "receiver_vpa": transaction.receiver_vpa,
            "amount": transaction.amount,
            "city": transaction.city,
            "decision": result.decision,
            "risk_score": result.risk_score,
            "latency_ms": result.inference_latency_ms,
            "shap_features": [
                {
                    "feature_name": f.feature_name,
                    "value": f.value,
                    "shap_value": f.shap_value,
                    "impact": f.impact,
                }
                for f in result.shap_features[:8]
            ],
            "rule_triggers": result.rule_triggers,
            "model_version": result.model_version,
        },
        "timestamp": result.timestamp.isoformat(),
    }
    await manager.enqueue(ws_payload)

    await redis_client.incr("metrics:total_transactions", ttl=None)
    if result.decision == "BLOCK":
        await redis_client.incr("metrics:blocked_transactions", ttl=None)

    log.info(
        "Prediction complete",
        decision=result.decision,
        risk_score=result.risk_score,
        latency_ms=result.inference_latency_ms,
    )

    return result


@router.post(
    "/feedback/{transaction_id}",
    summary="Submit ground truth feedback for a transaction",
)
async def submit_feedback(
    transaction_id: str,
    is_fraud: bool,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit actual fraud label for model monitoring."""
    from sqlalchemy.future import select

    result = await db.execute(
        select(Transaction).where(Transaction.transaction_id == transaction_id)
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    tx.is_fraud_actual = is_fraud
    await db.commit()
    return {"status": "feedback recorded", "transaction_id": transaction_id}

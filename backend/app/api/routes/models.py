"""Model registry endpoints with audit logging."""

from datetime import datetime, timezone
from typing import List

import mlflow
import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user, record_audit_event
from app.models.user import ModelVersion, User
from app.schemas.schemas import ModelVersionResponse
from app.services.inference import inference_service

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/models", response_model=List[ModelVersionResponse])
async def list_model_versions(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """List all registered model versions."""
    result = await db.execute(
        select(ModelVersion).order_by(ModelVersion.created_at.desc()).limit(20)
    )
    versions = result.scalars().all()
    return [ModelVersionResponse.model_validate(v) for v in versions]


@router.post("/models/{model_id}/promote")
async def promote_model(
    model_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Promote a model version to Production (superuser only)."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser required")

    result = await db.execute(select(ModelVersion).where(ModelVersion.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model version not found")

    current_result = await db.execute(
        select(ModelVersion).where(ModelVersion.is_active == True)
    )
    for current in current_result.scalars().all():
        current.is_active = False
        current.stage = "Archived"

    model.is_active = True
    model.stage = "Production"
    model.promoted_at = datetime.now(timezone.utc)
    await db.commit()

    new_version = await inference_service.reload_model()
    logger.info("Model promoted to Production", model_id=model_id)

    await record_audit_event(
        db=db,
        user_id=str(current_user.id),
        action="MODEL_PROMOTED",
        resource="model_version",
        resource_id=str(model_id),
        details={"model_name": model.model_name, "new_version": new_version},
        ip_address="",
    )

    return {"status": "promoted", "model_id": model_id, "loaded_version": new_version}


@router.post("/models/rollback")
async def rollback_model(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rollback to previous production model version (superuser only)."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser required")

    result = await db.execute(
        select(ModelVersion).order_by(ModelVersion.created_at.desc()).limit(2)
    )
    versions = result.scalars().all()
    if len(versions) < 2:
        raise HTTPException(status_code=400, detail="No previous version to rollback to")

    current, previous = versions[0], versions[1]
    current.is_active = False
    current.stage = "Archived"
    previous.is_active = True
    previous.stage = "Production"
    previous.promoted_at = datetime.now(timezone.utc)
    await db.commit()

    await inference_service.reload_model()
    logger.info("Model rolled back", from_version=current.id, to_version=previous.id)

    await record_audit_event(
        db=db,
        user_id=str(current_user.id),
        action="MODEL_ROLLED_BACK",
        resource="model_version",
        resource_id=str(previous.id),
        details={
            "from_version": current.mlflow_version,
            "to_version": previous.mlflow_version,
        },
        ip_address="",
    )

    return {"status": "rolled_back", "active_version": previous.mlflow_version}


@router.get("/drift-reports")
async def list_drift_reports(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """List recent drift detection reports."""
    from app.models.user import DriftReport
    from app.schemas.schemas import DriftReportResponse

    result = await db.execute(
        select(DriftReport).order_by(DriftReport.created_at.desc()).limit(20)
    )
    reports = result.scalars().all()
    return [DriftReportResponse.model_validate(r) for r in reports]

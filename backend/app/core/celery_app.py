"""Celery configuration and retraining tasks."""

import os
import subprocess
import sys
from datetime import datetime, timezone

import structlog
from celery import Celery

from app.core.config import settings

logger = structlog.get_logger(__name__)

celery_app = Celery(
    "upi_fraud",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.core.celery_app"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_soft_time_limit=600,
    task_time_limit=900,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=100,
    task_reject_on_worker_lost=True,
)


@celery_app.task(
    bind=True,
    name="retrain_model",
    queue="retrain",
    max_retries=2,
    default_retry_delay=60,
)
def retrain_model_task(self, drift_score: float, drift_report_id: str) -> dict:
    """
    Background task: retrain XGBoost on latest data.
    Triggered when Evidently detects concept drift.
    """
    logger.info(
        "Starting model retraining",
        drift_score=drift_score,
        report_id=drift_report_id,
        task_id=self.request.id,
    )

    try:
        self.update_state(state="PROGRESS", meta={"stage": "training", "progress": 10})

        env = {
            **os.environ,
            "MLFLOW_TRACKING_URI": settings.MLFLOW_TRACKING_URI,
            "POSTGRES_HOST": settings.POSTGRES_HOST,
            "POSTGRES_USER": settings.POSTGRES_USER,
            "POSTGRES_PASSWORD": settings.POSTGRES_PASSWORD,
            "POSTGRES_DB": settings.POSTGRES_DB,
            "REDIS_URL": settings.REDIS_URL,
        }

        process = subprocess.Popen(
            [sys.executable, "/mlops/training/train.py", "--retrain", "--drift-triggered"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )

        stdout, stderr = process.communicate(timeout=600)

        if process.returncode != 0:
            logger.error("Training script failed", stderr=stderr[-500:])
            raise RuntimeError(f"Training failed: {stderr[-500:]}")

        self.update_state(state="PROGRESS", meta={"stage": "registering", "progress": 90})

        logger.info("Model retraining completed successfully")

        import json
        import redis

        r = redis.from_url(settings.REDIS_URL)
        r.publish(
            "model_updates",
            json.dumps({
                "event": "model_retrained",
                "drift_score": drift_score,
                "report_id": drift_report_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }),
        )
        r.set("last_retrain_time", datetime.now(timezone.utc).isoformat())

        return {"status": "success", "drift_score": drift_score}

    except subprocess.TimeoutExpired:
        logger.error("Training timed out after 600s")
        raise self.retry(exc=RuntimeError("Training timed out"), countdown=120)

    except Exception as e:
        logger.error("Retraining task failed", error=str(e))
        raise self.retry(exc=e, countdown=60, max_retries=2)

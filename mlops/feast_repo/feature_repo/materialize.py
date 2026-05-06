"""
Feast Materialization Script
Runs on a schedule (or triggered by training) to push offline features → Redis online store.
In production this would be an Airflow/Prefect job running every 5 minutes.
"""

import os
import sys
from datetime import datetime, timedelta, timezone

import structlog
from feast import FeatureStore

logger = structlog.get_logger(__name__)

FEAST_REPO_PATH = os.getenv("FEAST_REPO_PATH", "/mlops/feast_repo/feature_repo")
MATERIALIZATION_INTERVAL_HOURS = int(os.getenv("MATERIALIZATION_INTERVAL_HOURS", "1"))


def materialize():
    """Push recent feature data from offline → online (Redis) store."""
    store = FeatureStore(repo_path=FEAST_REPO_PATH)

    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(hours=MATERIALIZATION_INTERVAL_HOURS)

    logger.info(
        "Starting materialization",
        start=start_date.isoformat(),
        end=end_date.isoformat(),
        interval_hours=MATERIALIZATION_INTERVAL_HOURS,
    )

    try:
        store.materialize_incremental(end_date=end_date)
        logger.info("Materialization complete")
    except Exception as e:
        logger.error("Materialization failed", error=str(e))
        # Non-fatal: inference falls back to Redis velocity counters
        sys.exit(0)


if __name__ == "__main__":
    materialize()

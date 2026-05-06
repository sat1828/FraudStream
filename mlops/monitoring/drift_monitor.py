"""
Evidently AI Drift Monitor
- Runs every 500 transactions
- Detects feature distribution drift + prediction drift
- Triggers Celery retraining task when drift detected
- Saves HTML reports
- Publishes drift alerts via Redis pub/sub → WebSocket
"""

import json
import os
import signal
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import psycopg2
import redis
import structlog
from evidently import ColumnMapping
from evidently.metric_preset import DataDriftPreset
from evidently.metrics import DatasetDriftMetric
from evidently.report import Report

logger = structlog.get_logger(__name__)

POSTGRES_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", 5432)),
    "dbname": os.getenv("POSTGRES_DB", "upi_fraud"),
    "user": os.getenv("POSTGRES_USER", "upi_user"),
    "password": os.getenv("POSTGRES_PASSWORD", ""),
}
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
DRIFT_THRESHOLD = float(os.getenv("DRIFT_THRESHOLD", 0.1))
MONITOR_WINDOW = int(os.getenv("DRIFT_DETECTION_WINDOW", 500))
REPORTS_DIR = Path("/data/drift_reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

FEATURE_COLS = [
    "amount", "amount_log", "amount_velocity_5min", "amount_velocity_1h",
    "amount_velocity_24h", "txn_count_5min", "txn_count_1h", "txn_count_24h",
    "device_txn_count_1h", "device_txn_count_24h",
    "sender_unique_receivers_1h", "sender_unique_devices_24h",
    "receiver_txn_count_1h", "is_new_device", "is_new_receiver",
    "is_night_txn", "is_festival_day", "amount_zscore", "hour_of_day", "day_of_week",
]

_running = True


def _handle_shutdown(signum, frame):
    global _running
    logger.info("Drift monitor received shutdown signal")
    _running = False


signal.signal(signal.SIGTERM, _handle_shutdown)
signal.signal(signal.SIGINT, _handle_shutdown)


def get_reference_data() -> Optional[pd.DataFrame]:
    """Load reference data (pre-drift training set) for comparison."""
    ref_path = Path("/data/train.parquet")
    if not ref_path.exists():
        logger.warning("Reference data not found")
        return None
    df = pd.read_parquet(ref_path)
    return df[FEATURE_COLS].sample(min(2000, len(df)), random_state=42)


def get_recent_transactions(n: int = 500) -> Optional[pd.DataFrame]:
    """Fetch last N transactions with features from PostgreSQL."""
    conn = None
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        query = """
            SELECT features, risk_score, decision, initiated_at
            FROM transactions
            WHERE features IS NOT NULL
            ORDER BY created_at DESC
            LIMIT %s
        """
        df = pd.read_sql(query, conn, params=(n,))

        if len(df) < 100:
            return None

        features_expanded = pd.json_normalize(df["features"].apply(
            lambda x: x if isinstance(x, dict) else json.loads(x) if x else {}
        ))

        for col in FEATURE_COLS:
            if col not in features_expanded.columns:
                features_expanded[col] = 0.0

        return features_expanded[FEATURE_COLS].astype(float)

    except Exception as e:
        logger.error("Failed to fetch recent transactions", error=str(e))
        return None
    finally:
        if conn:
            conn.close()


def run_drift_detection(reference_df: pd.DataFrame, current_df: pd.DataFrame) -> dict:
    """Run Evidently drift report and return summary."""
    report = Report(metrics=[
        DataDriftPreset(drift_share=DRIFT_THRESHOLD),
        DatasetDriftMetric(),
    ])

    column_mapping = ColumnMapping(numerical_features=FEATURE_COLS)

    report.run(
        reference_data=reference_df,
        current_data=current_df,
        column_mapping=column_mapping,
    )

    report_dict = report.as_dict()

    drift_metric = None
    n_drifted = 0
    drifted_features = []

    for metric in report_dict.get("metrics", []):
        if metric.get("metric") == "DatasetDriftMetric":
            result = metric.get("result", {})
            drift_metric = result.get("dataset_drift", False)
            n_drifted = result.get("number_of_drifted_columns", 0)
            for col_name, col_result in result.get("drift_by_columns", {}).items():
                if col_result.get("drift_detected", False):
                    drifted_features.append(col_name)

    drift_score = n_drifted / len(FEATURE_COLS)

    report_id = str(uuid.uuid4())[:8]
    report_path = REPORTS_DIR / f"drift_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{report_id}.html"
    report.save_html(str(report_path))

    return {
        "drift_detected": drift_metric or drift_score > DRIFT_THRESHOLD,
        "drift_score": drift_score,
        "n_drifted_features": n_drifted,
        "drifted_features": drifted_features,
        "report_path": str(report_path),
    }


def save_drift_report_to_db(result: dict, window_start: datetime, window_end: datetime, n_transactions: int):
    """Save drift report to PostgreSQL."""
    conn = None
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO drift_reports
            (report_id, window_start, window_end, transaction_count, dataset_drift_score,
             n_drifted_features, drifted_features, drift_detected, retrain_triggered,
             report_html_path, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                str(uuid.uuid4()),
                window_start, window_end, n_transactions,
                result["drift_score"],
                result["n_drifted_features"],
                json.dumps(result["drifted_features"]),
                result["drift_detected"],
                result["drift_detected"],
                result["report_path"],
                datetime.now(timezone.utc),
            ),
        )
        conn.commit()
        cur.close()
        logger.info("Drift report saved to DB")
    except Exception as e:
        logger.error("Failed to save drift report", error=str(e))
    finally:
        if conn:
            conn.close()


def trigger_retraining(drift_score: float, report_id: str) -> None:
    """Trigger Celery retraining task via Redis."""
    try:
        r = redis.from_url(REDIS_URL)

        alert = {
            "event_type": "drift_alert",
            "payload": {
                "drift_score": drift_score,
                "threshold": DRIFT_THRESHOLD,
                "report_id": report_id,
                "message": f"Concept drift detected! Score: {drift_score:.3f}. Retraining initiated...",
                "severity": "high" if drift_score > 0.3 else "medium",
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        r.publish("ws_broadcast", json.dumps(alert))
        r.set("current_drift_score", str(drift_score))

        # Use Celery's proper task dispatch
        try:
            from celery import Celery
            celery_app = Celery(broker=CELERY_BROKER_URL)
            celery_app.send_task(
                "retrain_model",
                args=[drift_score, report_id],
                queue="retrain",
            )
            logger.warning("Retraining triggered via Celery", drift_score=drift_score)
        except Exception as celery_err:
            logger.error("Celery dispatch failed, falling back to Redis signal", error=str(celery_err))
            r.set("drift_retrain_pending", json.dumps({
                "drift_score": drift_score,
                "report_id": report_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }))

    except Exception as e:
        logger.error("Failed to trigger retraining", error=str(e))


def monitor_loop():
    """Main monitoring loop."""
    logger.info("Drift monitor started", window_size=MONITOR_WINDOW, threshold=DRIFT_THRESHOLD)

    reference_df = None
    for _ in range(30):
        reference_df = get_reference_data()
        if reference_df is not None:
            break
        logger.info("Waiting for reference data...")
        time.sleep(10)

    if reference_df is None:
        logger.error("No reference data available. Exiting.")
        return

    logger.info("Reference data loaded", n=len(reference_df))
    last_check_count = 0

    global _running
    while _running:
        try:
            conn = psycopg2.connect(**POSTGRES_CONFIG)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM transactions WHERE features IS NOT NULL")
            total_count = cur.fetchone()[0]
            cur.close()
            conn.close()

            new_transactions = total_count - last_check_count

            if new_transactions >= MONITOR_WINDOW:
                logger.info(
                    "Running drift detection",
                    new_transactions=new_transactions,
                    total=total_count,
                )

                window_start = datetime.now(timezone.utc)
                current_df = get_recent_transactions(n=MONITOR_WINDOW)

                if current_df is not None and len(current_df) >= 100:
                    result = run_drift_detection(reference_df, current_df)
                    window_end = datetime.now(timezone.utc)

                    save_drift_report_to_db(result, window_start, window_end, len(current_df))

                    logger.info(
                        "Drift detection complete",
                        drift_detected=result["drift_detected"],
                        drift_score=result["drift_score"],
                        n_drifted=result["n_drifted_features"],
                        drifted_features=result["drifted_features"][:5],
                    )

                    if result["drift_detected"]:
                        trigger_retraining(
                            result["drift_score"],
                            result["report_path"].split("/")[-1],
                        )

                    last_check_count = total_count
                else:
                    logger.warning("Insufficient data for drift detection")

            time.sleep(30)

        except Exception as e:
            logger.error("Drift monitor error", error=str(e))
            if _running:
                time.sleep(60)

    logger.info("Drift monitor stopped gracefully")


if __name__ == "__main__":
    monitor_loop()

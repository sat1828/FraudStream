"""
UPI Fraud Detection Model Training Pipeline
- Loads data from Parquet (offline feature store)
- Trains XGBoost with MLflow tracking
- Logs metrics, artifacts, SHAP plots
- Registers model in MLflow Registry using model aliases
- Saves model version to PostgreSQL
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import mlflow
import mlflow.xgboost
import numpy as np
import pandas as pd
import shap
import structlog
import xgboost as xgb
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

logger = structlog.get_logger(__name__)

FEATURE_COLS = [
    "amount", "amount_log", "amount_velocity_5min", "amount_velocity_1h",
    "amount_velocity_24h", "txn_count_5min", "txn_count_1h", "txn_count_24h",
    "device_txn_count_1h", "device_txn_count_24h",
    "sender_unique_receivers_1h", "sender_unique_devices_24h",
    "receiver_txn_count_1h", "is_new_device", "is_new_receiver",
    "is_night_txn", "is_festival_day", "amount_zscore", "hour_of_day", "day_of_week",
]
TARGET_COL = "is_fraud"
DATA_DIR = Path("/data")


def load_data(retrain: bool = False) -> tuple:
    """Load training and validation data."""
    if retrain:
        full_path = DATA_DIR / "full_dataset.parquet"
        if not full_path.exists():
            raise FileNotFoundError(f"Full dataset not found: {full_path}")
        df = pd.read_parquet(full_path)
        train_df, val_df = train_test_split(df, test_size=0.2, random_state=42, stratify=df[TARGET_COL])
    else:
        train_path = DATA_DIR / "train.parquet"
        test_path = DATA_DIR / "test.parquet"
        if not train_path.exists():
            raise FileNotFoundError(
                f"Training data not found: {train_path}. Run generate_training_data.py first."
            )
        train_df = pd.read_parquet(train_path)
        val_df = pd.read_parquet(test_path)

    logger.info(
        "Data loaded",
        train_n=len(train_df),
        val_n=len(val_df),
        train_fraud_rate=f"{train_df[TARGET_COL].mean():.2%}",
        val_fraud_rate=f"{val_df[TARGET_COL].mean():.2%}",
    )
    return train_df, val_df


def get_xgboost_params() -> dict:
    """XGBoost hyperparameters optimized for fraud detection."""
    return {
        "n_estimators": 500,
        "max_depth": 7,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_weight": 5,
        "gamma": 0.1,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
        "scale_pos_weight": 40,
        "tree_method": "hist",
        "eval_metric": ["auc", "aucpr"],
        "random_state": 42,
        "n_jobs": -1,
        "verbosity": 0,
    }


def train_model(train_df: pd.DataFrame, val_df: pd.DataFrame, experiment_name: str) -> str:
    """Train XGBoost and log to MLflow. Returns run_id."""

    mlflow_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    mlflow.set_tracking_uri(mlflow_uri)
    mlflow.set_experiment(experiment_name)

    X_train = train_df[FEATURE_COLS].values.astype(np.float32)
    y_train = train_df[TARGET_COL].values.astype(int)
    X_val = val_df[FEATURE_COLS].values.astype(np.float32)
    y_val = val_df[TARGET_COL].values.astype(int)

    params = get_xgboost_params()

    with mlflow.start_run() as run:
        run_id = run.info.run_id
        logger.info("MLflow run started", run_id=run_id)

        mlflow.log_params(params)
        mlflow.log_param("train_samples", len(X_train))
        mlflow.log_param("val_samples", len(X_val))
        mlflow.log_param("fraud_rate_train", float(y_train.mean()))
        mlflow.log_param("feature_count", len(FEATURE_COLS))

        model = xgb.XGBClassifier(**params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            early_stopping_rounds=30,
            verbose=False,
        )

        y_pred_proba = model.predict_proba(X_val)[:, 1]
        y_pred = (y_pred_proba >= 0.5).astype(int)

        auc = roc_auc_score(y_val, y_pred_proba)
        pr_auc = average_precision_score(y_val, y_pred_proba)
        precision = precision_score(y_val, y_pred, zero_division=0)
        recall = recall_score(y_val, y_pred, zero_division=0)
        f1 = f1_score(y_val, y_pred, zero_division=0)

        cm = confusion_matrix(y_val, y_pred)
        tn, fp, fn, tp = cm.ravel()
        fpr = fp / (fp + tn + 1e-8)

        metrics = {
            "val_auc": auc,
            "val_pr_auc": pr_auc,
            "val_precision": precision,
            "val_recall": recall,
            "val_f1": f1,
            "val_fpr": fpr,
            "true_positives": int(tp),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_negatives": int(tn),
        }
        mlflow.log_metrics(metrics)

        logger.info(
            "Model evaluation",
            auc=f"{auc:.4f}",
            pr_auc=f"{pr_auc:.4f}",
            precision=f"{precision:.4f}",
            recall=f"{recall:.4f}",
            f1=f"{f1:.4f}",
            fpr=f"{fpr:.6f}",
        )

        explainer = shap.TreeExplainer(model)
        shap_sample = X_val[:500]
        shap_values = explainer.shap_values(shap_sample)

        feature_importance = pd.DataFrame({
            "feature": FEATURE_COLS,
            "importance_gain": model.feature_importances_,
            "mean_abs_shap": np.abs(shap_values).mean(axis=0),
        }).sort_values("mean_abs_shap", ascending=False)

        fi_path = DATA_DIR / "feature_importance.csv"
        feature_importance.to_csv(fi_path, index=False)
        mlflow.log_artifact(str(fi_path), "reports")

        for _, row in feature_importance.iterrows():
            mlflow.log_metric(f"fi_{row['feature']}", row["mean_abs_shap"])

        report = classification_report(y_val, y_pred, output_dict=True)
        report_path = DATA_DIR / "classification_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        mlflow.log_artifact(str(report_path), "reports")

        mlflow.xgboost.log_model(
            model,
            artifact_path="model",
            registered_model_name="upi-fraud-xgboost",
            input_example=pd.DataFrame([X_val[0]], columns=FEATURE_COLS),
        )

        if auc > 0.90:
            client = mlflow.tracking.MlflowClient()
            model_name = "upi-fraud-xgboost"
            versions = client.search_model_versions(
                f"name='{model_name}'",
                order_by=["version_number DESC"],
                max_results=1,
            )
            if versions:
                latest_version = versions[0].version
                try:
                    client.set_registered_model_alias(
                        name=model_name,
                        alias="production",
                        version=latest_version,
                    )
                    logger.info("Model aliased as Production", version=latest_version, auc=auc)
                except Exception as e:
                    logger.warning("Could not set MLflow alias (old MLflow version?)", error=str(e))

        _save_model_version_to_db(run_id, metrics, params, len(X_train))

        print(f"\n{'='*60}")
        print(f"Training complete!")
        print(f"   AUC:       {auc:.4f}")
        print(f"   PR-AUC:    {pr_auc:.4f}")
        print(f"   Precision: {precision:.4f}")
        print(f"   Recall:    {recall:.4f}")
        print(f"   F1:        {f1:.4f}")
        print(f"   FPR:       {fpr:.6f}")
        print(f"   Run ID:    {run_id}")
        print(f"{'='*60}\n")

        return run_id


def _save_model_version_to_db(run_id: str, metrics: dict, params: dict, n_train: int):
    """Persist model version info to PostgreSQL."""
    try:
        import psycopg2

        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            dbname=os.getenv("POSTGRES_DB", "upi_fraud"),
            user=os.getenv("POSTGRES_USER", "upi_user"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
        )
        cur = conn.cursor()

        cur.execute("UPDATE model_versions SET is_active = FALSE WHERE is_active = TRUE")

        mlflow_client = mlflow.tracking.MlflowClient()
        versions = mlflow_client.search_model_versions(
            "name='upi-fraud-xgboost'",
            order_by=["version_number DESC"],
            max_results=1,
        )
        mlflow_version = versions[0].version if versions else "1"

        cur.execute(
            """
            INSERT INTO model_versions
            (mlflow_run_id, mlflow_version, model_name, stage, train_auc, val_auc,
             precision, recall, f1_score, fpr, training_samples, feature_names, is_active, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                run_id, str(mlflow_version), "upi-fraud-xgboost", "Production",
                metrics.get("val_auc"), metrics.get("val_auc"),
                metrics.get("val_precision"), metrics.get("val_recall"),
                metrics.get("val_f1"), metrics.get("val_fpr"),
                n_train,
                json.dumps(FEATURE_COLS), True,
                datetime.now(timezone.utc),
            ),
        )
        conn.commit()
        cur.close()
        conn.close()

        import redis
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
        r.set("current_model_version", f"v{mlflow_version}")

        logger.info("Model version saved to DB", run_id=run_id, version=mlflow_version)

    except Exception as e:
        logger.warning("Failed to save model version to DB (non-critical)", error=str(e))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train UPI Fraud Detection Model")
    parser.add_argument("--retrain", action="store_true", help="Retrain on full dataset (drift recovery)")
    parser.add_argument("--drift-triggered", action="store_true", help="Flag: triggered by drift detection")
    parser.add_argument("--experiment", default="upi-fraud-detection", help="MLflow experiment name")
    args = parser.parse_args()

    logger.info(
        "Starting training pipeline",
        retrain=args.retrain,
        drift_triggered=args.drift_triggered,
    )

    try:
        train_df, val_df = load_data(retrain=args.retrain)
        run_id = train_model(train_df, val_df, args.experiment)
        logger.info("Training pipeline complete", run_id=run_id)
        sys.exit(0)
    except Exception as e:
        logger.error("Training pipeline failed", error=str(e))
        import traceback
        traceback.print_exc()
        sys.exit(1)

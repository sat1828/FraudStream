"""SQLAlchemy ORM models for User, Transaction, ModelVersion, DriftReport, AuditLog."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    JSON,
    String,
    Text,
    ForeignKey,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, server_default="true", default=True)
    is_superuser = Column(Boolean, server_default="false", default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(String(64), unique=True, nullable=False, index=True)

    sender_vpa = Column(String(255), nullable=False, index=True)
    receiver_vpa = Column(String(255), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), server_default="'INR'", default="INR")

    device_id = Column(String(255))
    device_os = Column(String(50))
    ip_address = Column(String(45))
    city = Column(String(100))
    state = Column(String(100))

    initiated_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    is_festival_day = Column(Boolean, server_default="false", default=False)
    festival_name = Column(String(100), nullable=True)

    features = Column(JSON, nullable=True)

    risk_score = Column(Float, nullable=True)
    decision = Column(String(20), nullable=True)
    is_fraud_actual = Column(Boolean, nullable=True)

    shap_values = Column(JSON, nullable=True)
    rule_triggers = Column(JSON, nullable=True)
    explanation_text = Column(Text, nullable=True)

    model_version = Column(String(50), nullable=True)
    inference_latency_ms = Column(Float, nullable=True)

    __table_args__ = (
        Index("idx_tx_sender_time", "sender_vpa", "initiated_at"),
        Index("idx_tx_decision", "decision"),
        Index("idx_tx_risk", "risk_score"),
    )


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mlflow_run_id = Column(String(64), unique=True, nullable=False)
    mlflow_version = Column(String(20))
    model_name = Column(String(100), server_default="'upi-fraud-xgboost'", default="upi-fraud-xgboost")
    stage = Column(String(20), server_default="'Staging'", default="Staging")

    train_auc = Column(Float)
    val_auc = Column(Float)
    precision = Column(Float)
    recall = Column(Float)
    f1_score = Column(Float)
    fpr = Column(Float)

    drift_score = Column(Float, nullable=True)
    triggered_by_drift = Column(Boolean, server_default="false", default=False)

    training_samples = Column(Integer)
    feature_names = Column(JSON)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    promoted_at = Column(DateTime(timezone=True), nullable=True)

    is_active = Column(Boolean, server_default="false", default=False)


class DriftReport(Base):
    __tablename__ = "drift_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(String(64), unique=True, default=lambda: str(uuid.uuid4()))

    window_start = Column(DateTime(timezone=True))
    window_end = Column(DateTime(timezone=True))
    transaction_count = Column(Integer)

    dataset_drift_score = Column(Float)
    prediction_drift_score = Column(Float, nullable=True)
    n_drifted_features = Column(Integer)
    drifted_features = Column(JSON)

    drift_detected = Column(Boolean, server_default="false", default=False)
    retrain_triggered = Column(Boolean, server_default="false", default=False)

    report_html_path = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    resource = Column(String(100))
    resource_id = Column(String(64))
    details = Column(JSON)
    ip_address = Column(String(45))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

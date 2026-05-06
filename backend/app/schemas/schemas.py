"""Pydantic v2 request/response schemas."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    email: EmailStr
    password: str = Field(min_length=6)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserResponse"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: str
    full_name: Optional[str]
    is_superuser: bool


class TransactionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    transaction_id: str = Field(..., description="Unique transaction ID")
    sender_vpa: str = Field(..., description="Sender's VPA e.g. user@okicici")
    receiver_vpa: str = Field(..., description="Receiver's VPA")
    amount: float = Field(..., gt=0, le=10_000_000, description="Transaction amount in INR")
    device_id: str = Field(..., description="Device fingerprint")
    device_os: str = Field(default="Android")
    ip_address: str = Field(default="0.0.0.0")
    city: str = Field(default="Unknown")
    state: str = Field(default="Unknown")
    is_festival_day: bool = Field(default=False)
    festival_name: Optional[str] = None
    initiated_at: Optional[datetime] = None

    @field_validator("sender_vpa", "receiver_vpa")
    @classmethod
    def validate_vpa(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("VPA must contain '@'")
        parts = v.split("@")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError("VPA must be in format 'identifier@provider'")
        return v.lower().strip()


class SHAPFeature(BaseModel):
    feature_name: str
    value: float
    shap_value: float
    impact: str


class PredictionResponse(BaseModel):
    transaction_id: str
    decision: str
    risk_score: float = Field(..., ge=0.0, le=1.0)
    confidence: float
    shap_features: List[SHAPFeature]
    rule_triggers: List[str]
    explanation_text: str
    model_version: str
    inference_latency_ms: float
    timestamp: datetime


class TransactionListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    transaction_id: str
    sender_vpa: str
    receiver_vpa: str
    amount: float
    city: str
    risk_score: Optional[float]
    decision: Optional[str]
    inference_latency_ms: Optional[float]
    initiated_at: datetime


class TransactionListResponse(BaseModel):
    items: List[TransactionListItem]
    total: int
    page: int
    page_size: int


class ModelVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    mlflow_run_id: str
    mlflow_version: Optional[str]
    stage: str
    train_auc: Optional[float]
    val_auc: Optional[float]
    precision: Optional[float]
    recall: Optional[float]
    f1_score: Optional[float]
    fpr: Optional[float]
    drift_score: Optional[float]
    triggered_by_drift: bool
    training_samples: Optional[int]
    is_active: bool
    created_at: datetime


class DriftReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    report_id: str
    window_start: datetime
    window_end: datetime
    transaction_count: int
    dataset_drift_score: float
    n_drifted_features: int
    drifted_features: List[str]
    drift_detected: bool
    retrain_triggered: bool
    created_at: datetime


class SystemMetrics(BaseModel):
    total_transactions: int
    transactions_last_hour: int
    fraud_rate_percent: float
    avg_latency_ms: float
    p95_latency_ms: float
    current_model_version: str
    drift_score: float
    last_retrain: Optional[datetime]
    tps: float


class WSEvent(BaseModel):
    event_type: str
    payload: dict
    timestamp: datetime

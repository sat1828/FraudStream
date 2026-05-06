"""
Feast Feature Store — Production-Ready Definitions
UPI Fraud Detection: 20 features across 3 FeatureViews + 1 OnDemandFeatureView
Online store: Redis  (<10 ms lookup)
Offline store: Parquet (point-in-time correct training)

Compatible with feast==0.40.x
"""

from datetime import timedelta

from feast import Entity, FeatureService, FeatureView, Field, FileSource, RequestSource
from feast.on_demand_feature_view import on_demand_feature_view
from feast.types import Float32, Int32, String, Bool
import pandas as pd


# ─── Data Sources ─────────────────────────────────────────────────────────────
transactions_source = FileSource(
    name="transactions_parquet",
    path="/data/train.parquet",
    timestamp_field="initiated_at",
    created_timestamp_column="initiated_at",
)


# ─── Entities ─────────────────────────────────────────────────────────────────
sender_entity = Entity(
    name="sender_vpa",
    description="Sender UPI Virtual Payment Address (primary fraud signal)",
    join_keys=["sender_vpa"],
)

device_entity = Entity(
    name="device_id",
    description="Device hardware fingerprint used for session tracking",
    join_keys=["device_id"],
)


# ─── Feature View 1: Sender Velocity ─────────────────────────────────────────
# Sliding-window transaction counts and amount sums per VPA
# Refreshed every 5 min in the online store via materialize-incremental
sender_velocity_fv = FeatureView(
    name="sender_velocity_features",
    entities=[sender_entity],
    ttl=timedelta(hours=24),
    schema=[
        Field(name="txn_count_5min",          dtype=Float32, description="Txn count in last 5 min"),
        Field(name="txn_count_1h",             dtype=Float32, description="Txn count in last 1 h"),
        Field(name="txn_count_24h",            dtype=Float32, description="Txn count in last 24 h"),
        Field(name="amount_velocity_5min",     dtype=Float32, description="Sum of amounts in 5 min (INR)"),
        Field(name="amount_velocity_1h",       dtype=Float32, description="Sum of amounts in 1 h (INR)"),
        Field(name="amount_velocity_24h",      dtype=Float32, description="Sum of amounts in 24 h (INR)"),
        Field(name="sender_unique_receivers_1h", dtype=Float32, description="Distinct receivers in 1 h"),
        Field(name="sender_unique_devices_24h",  dtype=Float32, description="Distinct devices in 24 h"),
        Field(name="amount_zscore",            dtype=Float32, description="Amount z-score vs sender history"),
        Field(name="amount_log",               dtype=Float32, description="log1p(amount)"),
    ],
    source=transactions_source,
    online=True,
    tags={
        "team": "fraud-ml",
        "version": "v2",
        "slo_ms": "10",
        "owner": "fraud-platform",
    },
    description="Sender-level velocity, aggregation, and normalisation features",
)


# ─── Feature View 2: Device Signals ──────────────────────────────────────────
device_features_fv = FeatureView(
    name="device_features",
    entities=[device_entity],
    ttl=timedelta(hours=48),
    schema=[
        Field(name="device_txn_count_1h",  dtype=Float32, description="Txns from this device in 1 h"),
        Field(name="device_txn_count_24h", dtype=Float32, description="Txns from this device in 24 h"),
        Field(name="is_new_device",        dtype=Float32, description="1 if first-ever seen device for this VPA"),
    ],
    source=transactions_source,
    online=True,
    tags={"team": "fraud-ml", "version": "v2"},
    description="Device-level transaction features for account-takeover detection",
)


# ─── Feature View 3: Transaction Context ────────────────────────────────────
# Temporal + receiver-side signals stored per sender_vpa
transaction_context_fv = FeatureView(
    name="transaction_context_features",
    entities=[sender_entity],
    ttl=timedelta(hours=2),
    schema=[
        Field(name="is_new_receiver",       dtype=Float32, description="1 if first txn to this receiver"),
        Field(name="receiver_txn_count_1h", dtype=Float32, description="Incoming txns to receiver in 1 h"),
        Field(name="is_night_txn",          dtype=Float32, description="1 if hour in [23, 0-5]"),
        Field(name="is_festival_day",       dtype=Float32, description="1 if national festival (Diwali, Holi…)"),
        Field(name="hour_of_day",           dtype=Float32, description="Hour 0–23"),
        Field(name="day_of_week",           dtype=Float32, description="Day 0 (Mon) – 6 (Sun)"),
    ],
    source=transactions_source,
    online=True,
    tags={"team": "fraud-ml", "version": "v2"},
    description="Temporal and receiver-side context features",
)


# ─── On-Demand Feature View: Derived at request time ─────────────────────────
# These are computed in real-time from request payload — zero latency fetch needed
input_request = RequestSource(
    name="transaction_request",
    schema=[
        Field(name="amount",    dtype=Float32),
        Field(name="hour",      dtype=Int32),
        Field(name="is_festival", dtype=Bool),
    ],
)

@on_demand_feature_view(
    sources=[input_request],
    schema=[
        Field(name="is_high_value",   dtype=Float32, description="1 if amount > 50,000 INR"),
        Field(name="is_round_amount", dtype=Float32, description="1 if amount is a round number (fraud signal)"),
        Field(name="is_just_under",   dtype=Float32, description="1 if 45000 < amount < 50000 (structuring)"),
    ],
)
def derived_transaction_features(inputs: pd.DataFrame) -> pd.DataFrame:
    """
    On-demand features computed at inference time from the raw request.
    No database lookup required — pure arithmetic on the incoming payload.
    """
    df = pd.DataFrame()
    df["is_high_value"]   = (inputs["amount"] > 50_000).astype(float)
    df["is_round_amount"] = (inputs["amount"] % 1000 == 0).astype(float)
    df["is_just_under"]   = ((inputs["amount"] > 45_000) & (inputs["amount"] < 50_000)).astype(float)
    return df


# ─── Feature Service ─────────────────────────────────────────────────────────
# Registered as a single logical unit for the inference API to call
fraud_detection_v2 = FeatureService(
    name="fraud_detection_v2",
    features=[
        sender_velocity_fv,
        device_features_fv,
        transaction_context_fv,
        # on-demand views are included automatically when used in get_online_features
    ],
    logging_config=None,   # Set to LoggingConfig(destination=...) for prod audit trail
    description="Production feature service — UPI fraud detection inference v2",
    tags={"slo_ms": "10", "version": "v2", "status": "production"},
)

# ─── Legacy alias (keeps backward-compat with any code referencing v1) ───────
fraud_detection_service = fraud_detection_v2

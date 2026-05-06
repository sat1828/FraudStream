"""
UPI Synthetic Data Generator
Generates ~100k realistic UPI transactions with:
- Realistic VPA patterns (banks, wallets)
- Fraud rings (mule accounts)
- Festival spikes
- Device patterns
- Concept drift injection (fraud patterns change mid-stream)
"""

import os
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pandas as pd
import structlog
from faker import Faker

logger = structlog.get_logger(__name__)
fake = Faker("en_IN")
np.random.seed(42)
random.seed(42)

# ─── Constants ────────────────────────────────────────────────────────────────
UPI_BANKS = ["okicici", "oksbi", "okhdfcbank", "okaxis", "ybl", "paytm", "upi", "ibl"]
MULE_VPA_POOL = [f"mule{i:04d}@paytm" for i in range(200)]
LEGIT_USER_POOL = [f"user{fake.numerify('######')}@{random.choice(UPI_BANKS)}" for _ in range(5000)]
MERCHANT_POOL = [f"{fake.company().lower().replace(' ', '')}@{random.choice(UPI_BANKS)}" for _ in range(500)]

INDIAN_CITIES = [
    ("Mumbai", "Maharashtra"), ("Delhi", "Delhi"), ("Bengaluru", "Karnataka"),
    ("Chennai", "Tamil Nadu"), ("Kolkata", "West Bengal"), ("Hyderabad", "Telangana"),
    ("Pune", "Maharashtra"), ("Ahmedabad", "Gujarat"), ("Jaipur", "Rajasthan"),
    ("Lucknow", "Uttar Pradesh"), ("Bhubaneswar", "Odisha"), ("Indore", "Madhya Pradesh"),
]

FESTIVALS = [
    ("Diwali", 0.15), ("Holi", 0.10), ("Dussehra", 0.08),
    ("Navratri", 0.07), ("Eid", 0.08), ("Christmas", 0.06),
    ("New Year", 0.05), ("None", 0.41),
]

DEVICE_POOL = [f"DEV-{uuid.uuid4().hex[:12].upper()}" for _ in range(3000)]

DATA_DIR = Path("/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)


def generate_transaction(
    tx_id: str,
    timestamp: datetime,
    fraud_pattern: str = "normal",
    fraud_probability: float = 0.02,
) -> dict:
    """Generate a single synthetic UPI transaction."""
    is_fraud = random.random() < fraud_probability

    city, state = random.choice(INDIAN_CITIES)
    device_id = random.choice(DEVICE_POOL)
    hour = timestamp.hour

    # Festival check
    festival_weights = [f[1] for f in FESTIVALS]
    festival_name = random.choices([f[0] for f in FESTIVALS], weights=festival_weights)[0]
    is_festival = festival_name != "None"

    if is_fraud:
        tx = _generate_fraud_transaction(
            tx_id, timestamp, fraud_pattern, city, state, device_id, is_festival, festival_name
        )
    else:
        tx = _generate_legit_transaction(
            tx_id, timestamp, city, state, device_id, is_festival, festival_name, hour
        )

    return tx


def _generate_legit_transaction(
    tx_id, ts, city, state, device_id, is_festival, festival_name, hour
) -> dict:
    sender = random.choice(LEGIT_USER_POOL)
    receiver = random.choice(MERCHANT_POOL + LEGIT_USER_POOL[:1000])

    # Realistic amount distribution
    if is_festival:
        amount = np.random.lognormal(mean=8.5, sigma=1.2)  # Higher during festivals
    elif 0 <= hour < 6:
        amount = np.random.lognormal(mean=6.5, sigma=0.8)  # Low at night
    else:
        amount = np.random.lognormal(mean=7.5, sigma=1.0)

    amount = round(min(max(amount, 1), 50000), 2)

    return {
        "transaction_id": tx_id,
        "sender_vpa": sender,
        "receiver_vpa": receiver,
        "amount": amount,
        "device_id": device_id,
        "device_os": random.choices(["Android", "iOS"], weights=[0.78, 0.22])[0],
        "ip_address": fake.ipv4(),
        "city": city,
        "state": state,
        "is_festival_day": is_festival,
        "festival_name": festival_name if is_festival else None,
        "is_fraud": False,
        "fraud_type": None,
        "initiated_at": ts.isoformat(),
    }


def _generate_fraud_transaction(
    tx_id, ts, fraud_pattern, city, state, device_id, is_festival, festival_name
) -> dict:
    """Generate fraud transaction based on pattern."""
    fraud_type = fraud_pattern

    if fraud_pattern == "normal" or fraud_pattern == "mule_ring":
        # Mule account ring: sends to mule VPAs
        sender = random.choice(LEGIT_USER_POOL[:200])  # Compromised accounts
        receiver = random.choice(MULE_VPA_POOL)
        amount = round(random.uniform(9000, 49999), 2)  # Just under 50k limit

    elif fraud_pattern == "account_takeover":
        # New device, high amount, unusual hour
        sender = random.choice(LEGIT_USER_POOL[:100])
        receiver = random.choice(MULE_VPA_POOL)
        amount = round(random.uniform(20000, 200000), 2)
        device_id = f"NEW-DEV-{uuid.uuid4().hex[:8].upper()}"  # New device

    elif fraud_pattern == "velocity_fraud":
        # Many small transactions rapidly
        sender = random.choice(LEGIT_USER_POOL[:50])
        receiver = random.choice(MULE_VPA_POOL)
        amount = round(random.uniform(100, 999), 2)

    elif fraud_pattern == "festival_fraud":
        # Exploit festival high-amount tolerance
        sender = random.choice(LEGIT_USER_POOL[:300])
        receiver = random.choice(MULE_VPA_POOL)
        amount = round(random.uniform(50000, 500000), 2)

    elif fraud_pattern == "deep_fake_vpa":
        # NEW DRIFT PATTERN: Deep-fake VPAs that look legitimate
        legit_merchant = random.choice(MERCHANT_POOL)
        # Slightly modify VPA
        sender = random.choice(LEGIT_USER_POOL)
        receiver = legit_merchant.replace("@", f"{random.randint(1,9)}@")
        amount = round(random.uniform(1000, 30000), 2)
        fraud_type = "deep_fake_vpa"

    else:
        sender = random.choice(LEGIT_USER_POOL[:200])
        receiver = random.choice(MULE_VPA_POOL)
        amount = round(random.uniform(5000, 100000), 2)

    return {
        "transaction_id": tx_id,
        "sender_vpa": sender,
        "receiver_vpa": receiver,
        "amount": amount,
        "device_id": device_id,
        "device_os": random.choices(["Android", "iOS"], weights=[0.78, 0.22])[0],
        "ip_address": fake.ipv4(),
        "city": city,
        "state": state,
        "is_festival_day": is_festival,
        "festival_name": festival_name if is_festival else None,
        "is_fraud": True,
        "fraud_type": fraud_type,
        "initiated_at": ts.isoformat(),
    }


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute ML features from raw transactions."""
    logger.info("Computing features...", n_transactions=len(df))

    df = df.sort_values("initiated_at").copy()
    df["initiated_at"] = pd.to_datetime(df["initiated_at"])
    df["amount_log"] = np.log1p(df["amount"])
    df["hour_of_day"] = df["initiated_at"].dt.hour
    df["day_of_week"] = df["initiated_at"].dt.dayofweek
    df["is_night_txn"] = ((df["hour_of_day"] < 6) | (df["hour_of_day"] >= 23)).astype(int)
    df["is_festival_day"] = df["is_festival_day"].astype(int)

    # Rolling velocity features
    df = df.set_index("initiated_at")

    # Per-VPA rolling counts
    for window, col in [("5min", "txn_count_5min"), ("1h", "txn_count_1h"), ("24h", "txn_count_24h")]:
        df[col] = (
            df.groupby("sender_vpa")["amount"]
            .transform(lambda x: x.rolling(window, min_periods=1).count())
        )

    for window, col in [("5min", "amount_velocity_5min"), ("1h", "amount_velocity_1h"), ("24h", "amount_velocity_24h")]:
        df[col] = (
            df.groupby("sender_vpa")["amount"]
            .transform(lambda x: x.rolling(window, min_periods=1).sum())
        )

    # Device-based features
    for window, col in [("1h", "device_txn_count_1h"), ("24h", "device_txn_count_24h")]:
        df[col] = (
            df.groupby("device_id")["amount"]
            .transform(lambda x: x.rolling(window, min_periods=1).count())
        )

    # Unique receivers per sender in 1h
    df["sender_unique_receivers_1h"] = (
        df.groupby("sender_vpa")["receiver_vpa"]
        .transform(lambda x: x.rolling("1h", min_periods=1).apply(lambda s: s.nunique()))
    )

    # Unique devices per sender in 24h
    df["sender_unique_devices_24h"] = (
        df.groupby("sender_vpa")["device_id"]
        .transform(lambda x: x.rolling("24h", min_periods=1).apply(lambda s: s.nunique()))
    )

    # Receiver transaction count in 1h
    df["receiver_txn_count_1h"] = (
        df.groupby("receiver_vpa")["amount"]
        .transform(lambda x: x.rolling("1h", min_periods=1).count())
    )

    # New device/receiver flags (based on historical counts)
    device_counts = df.groupby("device_id").cumcount()
    df["is_new_device"] = (device_counts == 0).astype(int)

    receiver_seen = df.groupby(["sender_vpa", "receiver_vpa"]).cumcount()
    df["is_new_receiver"] = (receiver_seen == 0).astype(int)

    # Amount z-score vs sender's history
    df["sender_mean_amount"] = df.groupby("sender_vpa")["amount"].transform("mean")
    df["sender_std_amount"] = df.groupby("sender_vpa")["amount"].transform("std").fillna(1.0)
    df["amount_zscore"] = (df["amount"] - df["sender_mean_amount"]) / (df["sender_std_amount"] + 1e-8)
    df["amount_zscore"] = df["amount_zscore"].clip(-5, 5)

    df = df.reset_index()

    # Fill NaN
    feature_cols = [
        "amount", "amount_log", "amount_velocity_5min", "amount_velocity_1h", "amount_velocity_24h",
        "txn_count_5min", "txn_count_1h", "txn_count_24h",
        "device_txn_count_1h", "device_txn_count_24h",
        "sender_unique_receivers_1h", "sender_unique_devices_24h",
        "receiver_txn_count_1h",
        "is_new_device", "is_new_receiver", "is_night_txn", "is_festival_day",
        "amount_zscore", "hour_of_day", "day_of_week",
    ]
    df[feature_cols] = df[feature_cols].fillna(0)

    return df


def generate_dataset(n_transactions: int = 100_000) -> pd.DataFrame:
    """Generate full synthetic dataset."""
    logger.info("Generating synthetic UPI dataset", n=n_transactions)

    transactions = []
    start_date = datetime.now(timezone.utc) - timedelta(days=30)

    # Phase 1: Normal fraud patterns (first 80k)
    phase1_n = int(n_transactions * 0.8)
    for i in range(phase1_n):
        ts = start_date + timedelta(seconds=i * 0.5 + random.uniform(-0.5, 0.5))
        fraud_pattern = random.choices(
            ["normal", "mule_ring", "account_takeover", "velocity_fraud", "festival_fraud"],
            weights=[0.6, 0.15, 0.1, 0.1, 0.05],
        )[0]
        tx = generate_transaction(
            str(uuid.uuid4()), ts, fraud_pattern=fraud_pattern, fraud_probability=0.025
        )
        transactions.append(tx)

    # Phase 2: CONCEPT DRIFT - new fraud pattern emerges (last 20k)
    # Deep-fake VPA fraud becomes dominant
    phase2_n = n_transactions - phase1_n
    phase2_start = start_date + timedelta(seconds=phase1_n * 0.5)
    for i in range(phase2_n):
        ts = phase2_start + timedelta(seconds=i * 0.5 + random.uniform(-0.5, 0.5))
        fraud_pattern = random.choices(
            ["normal", "deep_fake_vpa", "mule_ring", "account_takeover"],
            weights=[0.4, 0.35, 0.15, 0.1],  # deep_fake_vpa becomes dominant
        )[0]
        tx = generate_transaction(
            str(uuid.uuid4()), ts, fraud_pattern=fraud_pattern, fraud_probability=0.04  # Higher fraud rate
        )
        transactions.append(tx)

    df = pd.DataFrame(transactions)
    logger.info("Raw transactions generated", n=len(df), fraud_rate=f"{df['is_fraud'].mean():.2%}")

    # Compute features
    df = compute_features(df)

    return df


if __name__ == "__main__":
    df = generate_dataset(n_transactions=100_000)

    # Split: pre-drift for training, post-drift for drift detection
    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:]

    # Save
    train_path = DATA_DIR / "train.parquet"
    test_path = DATA_DIR / "test.parquet"
    full_path = DATA_DIR / "full_dataset.parquet"

    train_df.to_parquet(train_path, index=False)
    test_df.to_parquet(test_path, index=False)
    df.to_parquet(full_path, index=False)

    logger.info(
        "Dataset saved",
        train_n=len(train_df),
        test_n=len(test_df),
        train_fraud_rate=f"{train_df['is_fraud'].mean():.2%}",
        test_fraud_rate=f"{test_df['is_fraud'].mean():.2%}",
        train_path=str(train_path),
        test_path=str(test_path),
    )
    print(f"✅ Dataset generated: {len(df):,} transactions, fraud rate: {df['is_fraud'].mean():.2%}")

"""
Real-Time UPI Transaction Producer
Streams synthetic transactions into Redpanda/Kafka.
After 60 seconds: injects CONCEPT DRIFT (new fraud pattern).
Simulates ~20 TPS.
"""

import json
import os
import random
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import structlog
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

sys.path.insert(0, str(Path(__file__).parent))
from generate_training_data import (
    DEVICE_POOL, INDIAN_CITIES, LEGIT_USER_POOL, MERCHANT_POOL, MULE_VPA_POOL,
    generate_transaction,
)

logger = structlog.get_logger(__name__)

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = "upi-raw-transactions"
DRIFT_AFTER_SECONDS = 60
TARGET_TPS = 20


def create_producer(retries: int = 10) -> KafkaProducer:
    """Create Kafka producer with retry logic."""
    for attempt in range(retries):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                compression_type="snappy",
                batch_size=32768,
                linger_ms=5,
                acks="all",
                retries=3,
            )
            logger.info("Kafka producer connected", broker=KAFKA_BOOTSTRAP)
            return producer
        except NoBrokersAvailable:
            logger.warning(f"Kafka not ready, retrying {attempt+1}/{retries}...")
            time.sleep(5)
    raise RuntimeError(f"Could not connect to Kafka at {KAFKA_BOOTSTRAP}")


def produce_transactions(producer: KafkaProducer):
    """Main production loop with drift injection."""
    start_time = time.time()
    tx_count = 0
    drift_injected = False

    logger.info(
        "Transaction producer started",
        topic=TOPIC,
        tps=TARGET_TPS,
        drift_after_seconds=DRIFT_AFTER_SECONDS,
    )

    interval = 1.0 / TARGET_TPS

    while True:
        loop_start = time.monotonic()
        elapsed = time.time() - start_time

        if elapsed > DRIFT_AFTER_SECONDS and not drift_injected:
            logger.warning(
                "CONCEPT DRIFT INJECTED: Deep-fake VPA fraud pattern now dominant!",
                elapsed_seconds=elapsed,
            )
            drift_injected = True

        now = datetime.now(timezone.utc)
        tx_id = f"TXN{now.strftime('%Y%m%d%H%M%S')}{tx_count:06d}"

        if drift_injected:
            fraud_pattern = random.choices(
                ["normal", "deep_fake_vpa", "deep_fake_vpa", "mule_ring"],
                weights=[0.5, 0.25, 0.15, 0.10],
            )[0]
            fraud_prob = 0.08
        else:
            fraud_pattern = random.choices(
                ["normal", "mule_ring", "account_takeover", "velocity_fraud"],
                weights=[0.65, 0.15, 0.12, 0.08],
            )[0]
            fraud_prob = 0.025

        tx = generate_transaction(
            tx_id=tx_id,
            timestamp=now,
            fraud_pattern=fraud_pattern,
            fraud_probability=fraud_prob,
        )

        tx["kafka_timestamp"] = now.isoformat()
        tx["drift_phase"] = "post_drift" if drift_injected else "pre_drift"
        tx["sequence_number"] = tx_count

        try:
            producer.send(
                TOPIC,
                value=tx,
                key=tx["sender_vpa"].encode("utf-8"),
            )
            tx_count += 1

            if tx_count % 100 == 0:
                logger.info(
                    "Producer heartbeat",
                    total_sent=tx_count,
                    elapsed_s=round(elapsed, 1),
                    drift_injected=drift_injected,
                    current_fraud_prob=fraud_prob,
                )
        except Exception as e:
            logger.error("Failed to produce message", error=str(e))

        elapsed_loop = time.monotonic() - loop_start
        sleep_time = max(0, interval - elapsed_loop)
        if sleep_time > 0:
            time.sleep(sleep_time)


if __name__ == "__main__":
    logger.info("Starting UPI Transaction Producer", kafka_broker=KAFKA_BOOTSTRAP)

    producer = create_producer()
    try:
        produce_transactions(producer)
    except KeyboardInterrupt:
        logger.info("Producer stopped by user")
    finally:
        producer.flush()
        producer.close()

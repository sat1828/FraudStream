"""
Kafka Consumer Service
Reads raw transactions from Redpanda → calls FastAPI /predict endpoint.
Closes the loop: Producer → Redpanda → Consumer → FastAPI → PostgreSQL.
"""

import asyncio
import json
import os
import time
from datetime import datetime, timezone

import httpx
import structlog
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable

logger = structlog.get_logger(__name__)

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = "upi-raw-transactions"
API_URL = os.getenv("BACKEND_URL", "http://backend:8000")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@upi.ai")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
CONSUMER_GROUP = "fraud-inference-group"

MAX_RETRIES = 10
RETRY_DELAY = 5
TOKEN_REFRESH_INTERVAL = 3600


def get_auth_token() -> str:
    """Authenticate and get JWT token using httpx."""
    for attempt in range(MAX_RETRIES):
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.post(
                    f"{API_URL}/api/v1/auth/login",
                    json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                )
                if resp.status_code == 200:
                    token = resp.json()["access_token"]
                    logger.info("Authenticated with backend", token_prefix=token[:20])
                    return token
                logger.warning(f"Auth attempt {attempt+1}/{MAX_RETRIES} failed: {resp.status_code}")
        except Exception as e:
            logger.warning(f"Auth attempt {attempt+1}/{MAX_RETRIES} failed", error=str(e))
        time.sleep(RETRY_DELAY)
    raise RuntimeError("Could not authenticate with backend")


def create_consumer(retries: int = MAX_RETRIES) -> KafkaConsumer:
    """Create Kafka consumer with retry."""
    for attempt in range(retries):
        try:
            consumer = KafkaConsumer(
                TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP,
                group_id=CONSUMER_GROUP,
                auto_offset_reset="latest",
                enable_auto_commit=True,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                consumer_timeout_ms=1000,
                max_poll_records=50,
            )
            logger.info("Kafka consumer connected", topic=TOPIC, group=CONSUMER_GROUP)
            return consumer
        except NoBrokersAvailable:
            logger.warning(f"Kafka not ready, retry {attempt+1}/{retries}")
            time.sleep(RETRY_DELAY)
    raise RuntimeError("Could not connect to Kafka")


async def process_batch(
    client: httpx.AsyncClient,
    messages: list,
    token: str,
) -> tuple:
    """Send batch of transactions to /predict API."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    success, errors = 0, 0

    tasks = []
    for msg in messages:
        payload = {
            "transaction_id": msg.get("transaction_id", f"AUTO-{int(time.time()*1000)}"),
            "sender_vpa": msg.get("sender_vpa", "unknown@upi"),
            "receiver_vpa": msg.get("receiver_vpa", "unknown@upi"),
            "amount": float(msg.get("amount", 0)),
            "device_id": msg.get("device_id", "UNKNOWN"),
            "device_os": msg.get("device_os", "Android"),
            "ip_address": msg.get("ip_address", "0.0.0.0"),
            "city": msg.get("city", "Unknown"),
            "state": msg.get("state", "Unknown"),
            "is_festival_day": bool(msg.get("is_festival_day", False)),
            "festival_name": msg.get("festival_name"),
            "initiated_at": msg.get("initiated_at"),
        }
        tasks.append(
            client.post(f"{API_URL}/api/v1/predict", json=payload, headers=headers)
        )

    responses = await asyncio.gather(*tasks, return_exceptions=True)
    for resp in responses:
        if isinstance(resp, Exception):
            errors += 1
        elif resp.status_code == 200:
            success += 1
        else:
            errors += 1
            if resp.status_code != 429:
                logger.warning("Predict failed", status=resp.status_code)

    return success, errors


async def consume_loop(token: str):
    """Main async consumption loop with token refresh."""
    consumer = create_consumer()
    total_processed = 0
    total_errors = 0
    start_time = time.time()
    last_token_refresh = time.time()
    current_token = token

    async with httpx.AsyncClient(timeout=30.0, limits=httpx.Limits(max_connections=20)) as client:
        logger.info("Consumer started, waiting for messages...")

        while True:
            elapsed_since_refresh = time.time() - last_token_refresh
            if elapsed_since_refresh > TOKEN_REFRESH_INTERVAL:
                try:
                    current_token = get_auth_token()
                    last_token_refresh = time.time()
                    logger.info("Token refreshed")
                except Exception as e:
                    logger.error("Token refresh failed", error=str(e))

            batch = []
            try:
                for message in consumer:
                    batch.append(message.value)
                    if len(batch) >= 10:
                        break
            except Exception:
                pass

            if batch:
                success, errors = await process_batch(client, batch, current_token)
                total_processed += success
                total_errors += errors
                elapsed = time.time() - start_time
                tps = total_processed / elapsed if elapsed > 0 else 0

                if total_processed % 100 == 0 and total_processed > 0:
                    logger.info(
                        "Consumer stats",
                        total_processed=total_processed,
                        total_errors=total_errors,
                        tps=round(tps, 2),
                        error_rate=f"{total_errors/(total_processed+total_errors)*100:.1f}%",
                    )
            else:
                await asyncio.sleep(0.1)


if __name__ == "__main__":
    logger.info("Starting Kafka consumer service")
    if not ADMIN_PASSWORD:
        logger.error("ADMIN_PASSWORD not set. Cannot authenticate.")
        exit(1)
    token = get_auth_token()
    asyncio.run(consume_loop(token))

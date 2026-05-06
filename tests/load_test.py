"""Locust load test for UPI Fraud Detection API."""

from locust import HttpUser, task, between, events
import json
import time


class FraudDetectionUser(HttpUser):
    """Simulates real-time fraud detection API usage."""

    wait_time = between(0.05, 0.2)
    token = None

    def on_start(self):
        """Login and store token."""
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"email": "admin@upi.ai", "password": "password"},
        )
        if resp.status_code == 200:
            self.token = resp.json().get("access_token")

    @task(8)
    def predict_normal(self):
        """Normal transaction prediction."""
        if not self.token:
            return

        self.client.post(
            "/api/v1/predict",
            json={
                "transaction_id": f"TXN-LOAD-{int(time.time()*1000)}",
                "sender_vpa": "user123@okicici",
                "receiver_vpa": "merchant@ybl",
                "amount": 5000.0,
                "device_id": "DEV-LOAD-001",
                "device_os": "Android",
                "city": "Mumbai",
                "is_festival_day": False,
            },
            headers={"Authorization": f"Bearer {self.token}"},
            name="/predict (normal)",
        )

    @task(1)
    def predict_high_risk(self):
        """High-risk transaction prediction."""
        if not self.token:
            return

        self.client.post(
            "/api/v1/predict",
            json={
                "transaction_id": f"TXN-LOAD-HIGH-{int(time.time()*1000)}",
                "sender_vpa": "victim@okicici",
                "receiver_vpa": "mule0001@paytm",
                "amount": 49999.0,
                "device_id": "NEW-DEV-LOAD",
                "device_os": "Android",
                "city": "Unknown",
                "is_festival_day": False,
            },
            headers={"Authorization": f"Bearer {self.token}"},
            name="/predict (high-risk)",
        )

    @task(1)
    def get_transactions(self):
        """Fetch transaction history."""
        if not self.token:
            return

        self.client.get(
            "/api/v1/transactions?page=1&page_size=20",
            headers={"Authorization": f"Bearer {self.token}"},
        )


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print summary statistics."""
    stats = environment.runner.stats
    print(f"\n{'='*60}")
    print(f"Load Test Summary")
    print(f"{'='*60}")
    print(f"Total requests: {stats.total.num_requests}")
    print(f"Total failures: {stats.total.num_failures}")
    if stats.total.num_requests > 0:
        print(f"Failure rate: {stats.total.num_failures/stats.total.num_requests*100:.2f}%")
        print(f"Avg response time: {stats.total.avg_response_time:.0f}ms")
        print(f"Median response time: {stats.total.median_response_time:.0f}ms")
        print(f"95th percentile: {stats.total.get_response_time_percentile(0.95):.0f}ms")
        print(f"99th percentile: {stats.total.get_response_time_percentile(0.99):.0f}ms")
    print(f"{'='*60}\n")

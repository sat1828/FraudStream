"""
ML Inference Service
- Loads model from MLflow Registry
- Computes real-time features from Redis counters
- Runs XGBoost prediction
- Generates SHAP explanations
- Applies hybrid rule engine
- Target: p95 latency < 80ms
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import structlog

from app.core.config import settings
from app.core.redis_client import redis_client
from app.schemas.schemas import PredictionResponse, SHAPFeature, TransactionRequest

logger = structlog.get_logger(__name__)

# Lazy-loaded modules
_nl = {}
def _get_ml_deps():
    """Lazily import ML dependencies only when needed."""
    if not _nl:
        import numpy as np
        import shap
        import xgboost as xgb
        import mlflow
        import mlflow.pyfunc
        _nl['np'] = np
        _nl['shap'] = shap
        _nl['xgb'] = xgb
        _nl['mlflow'] = mlflow
        _nl['mlflow_pyfunc'] = mlflow.pyfunc
    return _nl

FEATURE_NAMES = [
    "amount", "amount_log", "amount_velocity_5min", "amount_velocity_1h",
    "amount_velocity_24h", "txn_count_5min", "txn_count_1h", "txn_count_24h",
    "device_txn_count_1h", "device_txn_count_24h",
    "sender_unique_receivers_1h", "sender_unique_devices_24h",
    "receiver_txn_count_1h", "is_new_device", "is_new_receiver",
    "is_night_txn", "is_festival_day", "amount_zscore", "hour_of_day", "day_of_week",
]

RULES = {
    "BLOCK_AMOUNT_EXTREME": {"threshold": 500000, "score_boost": 0.9},
    "BLOCK_VELOCITY_HIGH": {"threshold": 10, "score_boost": 0.7},
    "BLOCK_NEW_DEVICE_HIGH_AMOUNT": {"threshold": 50000, "score_boost": 0.6},
    "REVIEW_NIGHT_HIGH": {"threshold": 25000, "score_boost": 0.3},
    "REVIEW_FESTIVAL_HIGH": {"threshold": 100000, "score_boost": 0.2},
}


class InferenceService:
    """Production ML inference service with caching and explainability."""

    def __init__(self):
        self._model: Optional[object] = None
        self._explainer: Optional[object] = None
        self._model_version: str = "unknown"
        self._model_loaded = False
        self._lock = asyncio.Lock()

    @property
    def is_ready(self) -> bool:
        return self._model_loaded

    @property
    def model_version(self) -> str:
        return self._model_version

    async def initialize(self) -> None:
        """Load model from MLflow and initialize Feast."""
        async with self._lock:
            if self._model_loaded:
                return
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._load_model)
            self._model_loaded = True
            logger.info("Inference service initialized", model_version=self._model_version)

    def _load_model(self) -> None:
        """Synchronous model loading (runs in thread pool)."""
        try:
            deps = _get_ml_deps()
            mlflow = deps['mlflow']
            
            mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
            client = mlflow.tracking.MlflowClient()

            try:
                model_name = settings.MLFLOW_MODEL_NAME
                aliases = client.get_registered_model(model_name).aliases
                if "production" in aliases:
                    version = aliases["production"]
                    model_uri = f"models:/{model_name}@production"
                else:
                    versions = client.search_model_versions(
                        f"name='{model_name}'",
                        order_by=["version_number DESC"],
                        max_results=1,
                    )
                    if not versions:
                        self._create_fallback_model()
                        return
                    version = versions[0].version
                    model_uri = f"models:/{model_name}/{version}"

                self._model_version = f"v{version}"
                loaded = mlflow.xgboost.load_model(model_uri)
                self._model = loaded
                
                # Only create explainer if model loaded successfully
                deps = _get_ml_deps()
                shap = deps['shap']
                self._explainer = shap.TreeExplainer(self._model)
                logger.info("Model loaded from MLflow Registry", version=self._model_version)
                return
            except Exception as e:
                logger.warning("MLflow model not found, using fallback", error=str(e))

            self._create_fallback_model()

        except Exception as e:
            logger.error("Failed to load model", error=str(e))
            self._create_fallback_model()

    def _create_fallback_model(self) -> None:
        """Create a minimal fallback model for startup."""
        logger.warning("Using fallback heuristic model")
        self._model = None
        self._model_version = "fallback-heuristic"

    async def reload_model(self) -> str:
        """Hot-reload model (called after retraining)."""
        async with self._lock:
            self._model_loaded = False
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._load_model)
            self._model_loaded = True
        return self._model_version

    async def _get_features(self, transaction: TransactionRequest) -> Dict[str, float]:
        """Compute real-time features from Redis counters."""
        cache_key = f"features:{transaction.sender_vpa}:{transaction.device_id}"

        cached = await redis_client.get_json(cache_key)
        if cached:
            return cached

        now = datetime.now(timezone.utc)
        hour = now.hour
        dow = now.weekday()

        vpa_5min_key = f"vel:{transaction.sender_vpa}:5min"
        vpa_1h_key = f"vel:{transaction.sender_vpa}:1h"
        vpa_24h_key = f"vel:{transaction.sender_vpa}:24h"
        device_1h_key = f"dev:{transaction.device_id}:1h"
        device_24h_key = f"dev:{transaction.device_id}:24h"
        amounts_key = f"amounts:{transaction.sender_vpa}:24h"

        results = await asyncio.gather(
            redis_client.get(vpa_5min_key),
            redis_client.get(vpa_1h_key),
            redis_client.get(vpa_24h_key),
            redis_client.get(device_1h_key),
            redis_client.get(device_24h_key),
            redis_client.get(f"avg_amount:{transaction.sender_vpa}"),
            redis_client.get(f"seen_device:{transaction.sender_vpa}:{transaction.device_id}"),
            redis_client.get(f"seen_receiver:{transaction.sender_vpa}:{transaction.receiver_vpa}"),
            return_exceptions=True,
        )

        def safe_int(val) -> int:
            if val and not isinstance(val, Exception):
                try:
                    return int(val)
                except (ValueError, TypeError):
                    pass
            return 0

        txn_count_5min = safe_int(results[0])
        txn_count_1h = safe_int(results[1])
        txn_count_24h = safe_int(results[2])
        device_1h = safe_int(results[3])
        device_24h = safe_int(results[4])
        avg_amount_raw = results[5]
        is_new_device = 0 if results[6] and not isinstance(results[6], Exception) else 1
        is_new_receiver = 0 if results[7] and not isinstance(results[7], Exception) else 1

        avg_amount = float(avg_amount_raw) if avg_amount_raw and not isinstance(avg_amount_raw, Exception) else transaction.amount
        amount_zscore = (transaction.amount - avg_amount) / (avg_amount + 1e-8)

        deps = _get_ml_deps()
        np = deps['np']
        
        features = {
            "amount": transaction.amount,
            "amount_log": float(np.log1p(transaction.amount)),
            "amount_velocity_5min": txn_count_5min * transaction.amount / 5.0 if txn_count_5min > 0 else 0.0,
            "amount_velocity_1h": txn_count_1h * transaction.amount / 60.0 if txn_count_1h > 0 else 0.0,
            "amount_velocity_24h": txn_count_24h * transaction.amount / 1440.0 if txn_count_24h > 0 else 0.0,
            "txn_count_5min": float(txn_count_5min),
            "txn_count_1h": float(txn_count_1h),
            "txn_count_24h": float(txn_count_24h),
            "device_txn_count_1h": float(device_1h),
            "device_txn_count_24h": float(device_24h),
            "sender_unique_receivers_1h": float(max(1.0, txn_count_1h)),
            "sender_unique_devices_24h": float(max(1.0, device_24h)),
            "receiver_txn_count_1h": 0.0,
            "is_new_device": float(is_new_device),
            "is_new_receiver": float(is_new_receiver),
            "is_night_txn": 1.0 if hour < 6 or hour >= 23 else 0.0,
            "is_festival_day": float(transaction.is_festival_day),
            "amount_zscore": float(np.clip(amount_zscore, -5, 5)),
            "hour_of_day": float(hour),
            "day_of_week": float(dow),
        }

        await redis_client.set(cache_key, features, ttl=30)
        await self._update_counters(transaction)

        return features

    async def _update_counters(self, tx: TransactionRequest) -> None:
        """Update Redis velocity counters after processing."""
        try:
            tasks = [
                redis_client.incr(f"vel:{tx.sender_vpa}:5min", ttl=300),
                redis_client.incr(f"vel:{tx.sender_vpa}:1h", ttl=3600),
                redis_client.incr(f"vel:{tx.sender_vpa}:24h", ttl=86400),
                redis_client.incr(f"dev:{tx.device_id}:1h", ttl=3600),
                redis_client.incr(f"dev:{tx.device_id}:24h", ttl=86400),
                redis_client.set(f"seen_device:{tx.sender_vpa}:{tx.device_id}", "1", ttl=86400 * 30),
                redis_client.set(f"seen_receiver:{tx.sender_vpa}:{tx.receiver_vpa}", "1", ttl=86400 * 30),
            ]
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logger.error("Failed to update counters", error=str(e))

    def _apply_rule_engine(
        self, transaction: TransactionRequest, features: Dict[str, float], base_score: float
    ) -> Tuple[float, List[str]]:
        """Apply business rules on top of ML score."""
        score = base_score
        triggered_rules = []

        if transaction.amount > RULES["BLOCK_AMOUNT_EXTREME"]["threshold"]:
            score = max(score, RULES["BLOCK_AMOUNT_EXTREME"]["score_boost"])
            triggered_rules.append(f"AMOUNT_EXCEEDS_{RULES['BLOCK_AMOUNT_EXTREME']['threshold']}")

        if features.get("txn_count_5min", 0) > RULES["BLOCK_VELOCITY_HIGH"]["threshold"]:
            score = max(score, RULES["BLOCK_VELOCITY_HIGH"]["score_boost"])
            triggered_rules.append("HIGH_TRANSACTION_VELOCITY_5MIN")

        if features.get("is_new_device", 0) == 1 and transaction.amount > RULES["BLOCK_NEW_DEVICE_HIGH_AMOUNT"]["threshold"]:
            score = max(score, RULES["BLOCK_NEW_DEVICE_HIGH_AMOUNT"]["score_boost"])
            triggered_rules.append("NEW_DEVICE_HIGH_AMOUNT")

        if features.get("is_night_txn", 0) == 1 and transaction.amount > RULES["REVIEW_NIGHT_HIGH"]["threshold"]:
            score = max(score, base_score + RULES["REVIEW_NIGHT_HIGH"]["score_boost"])
            triggered_rules.append("NIGHT_HIGH_AMOUNT")

        if transaction.is_festival_day and transaction.amount > RULES["REVIEW_FESTIVAL_HIGH"]["threshold"]:
            triggered_rules.append("FESTIVAL_HIGH_AMOUNT_REVIEW")

        return min(score, 1.0), triggered_rules

    def _score_to_decision(self, score: float) -> str:
        if score >= settings.MODEL_FRAUD_THRESHOLD:
            return "BLOCK"
        elif score >= settings.MODEL_REVIEW_THRESHOLD:
            return "REVIEW"
        return "ALLOW"

    def _generate_explanation(
        self, decision: str, score: float, shap_features: List[SHAPFeature], rules: List[str]
    ) -> str:
        top_feature = shap_features[0].feature_name if shap_features else "model"
        if decision == "BLOCK":
            return (
                f"Transaction BLOCKED with {score:.1%} fraud risk. "
                f"Primary signal: {top_feature.replace('_', ' ')}. "
                f"{'Rules triggered: ' + ', '.join(rules[:2]) if rules else 'ML model flagged anomalous pattern.'}"
            )
        elif decision == "REVIEW":
            return (
                f"Transaction flagged for REVIEW ({score:.1%} risk). "
                f"Suspicious pattern: {top_feature.replace('_', ' ')}. Manual verification recommended."
            )
        return f"Transaction ALLOWED ({score:.1%} risk). Pattern consistent with normal user behavior."

    async def predict(self, transaction: TransactionRequest) -> PredictionResponse:
        """Main inference pipeline. Target: p95 < 80 ms."""
        start_time = time.monotonic()

        if not self._model_loaded:
            await self.initialize()

        features = await self._get_features(transaction)
        
        deps = _get_ml_deps()
        np = deps['np']
        
        feature_vector = np.array([[features[f] for f in FEATURE_NAMES]], dtype=np.float32)

        if self._model is not None:
            loop = asyncio.get_running_loop()
            ml_score, shap_vals = await loop.run_in_executor(
                None, self._run_model, feature_vector
            )
        else:
            ml_score = self._heuristic_score(features)
            shap_vals = [0.0] * len(FEATURE_NAMES)

        final_score, triggered_rules = self._apply_rule_engine(transaction, features, ml_score)
        decision = self._score_to_decision(final_score)

        shap_features = []
        for i, (name, sval) in enumerate(zip(FEATURE_NAMES, shap_vals)):
            shap_features.append(
                SHAPFeature(
                    feature_name=name,
                    value=float(feature_vector[0][i]),
                    shap_value=float(sval),
                    impact="positive" if sval > 0 else "negative",
                )
            )
        shap_features.sort(key=lambda x: abs(x.shap_value), reverse=True)

        explanation = self._generate_explanation(decision, final_score, shap_features, triggered_rules)
        latency_ms = (time.monotonic() - start_time) * 1000

        await redis_client.lpush("latency:recent", latency_ms)

        if latency_ms > settings.INFERENCE_TIMEOUT_MS:
            logger.warning("Inference exceeded target latency", latency_ms=latency_ms)

        return PredictionResponse(
            transaction_id=transaction.transaction_id,
            decision=decision,
            risk_score=round(final_score, 4),
            confidence=abs(final_score - 0.5) * 2,
            shap_features=shap_features[:10],
            rule_triggers=triggered_rules,
            explanation_text=explanation,
            model_version=self._model_version,
            inference_latency_ms=round(latency_ms, 2),
            timestamp=datetime.now(timezone.utc),
        )

    def _run_model(self, feature_vector: object) -> Tuple[float, List[float]]:
        """Runs XGBoost + SHAP synchronously (called in thread pool)."""
        deps = _get_ml_deps()
        np = deps['np']
        shap = deps['shap']
        
        score = float(self._model.predict_proba(feature_vector)[0][1])

        shap_values = self._explainer.shap_values(feature_vector)
        if isinstance(shap_values, list):
            shap_vals = shap_values[1][0].tolist()
        else:
            shap_vals = shap_values[0].tolist()

        return score, shap_vals

    def _heuristic_score(self, features: Dict) -> float:
        """Fallback rule-based scoring when model not available."""
        score = 0.05
        if features.get("amount", 0) > 100000:
            score += 0.3
        if features.get("txn_count_5min", 0) > 5:
            score += 0.4
        if features.get("is_new_device", 0) == 1:
            score += 0.1
        if features.get("is_night_txn", 0) == 1:
            score += 0.05
        return min(score, 1.0)


inference_service = InferenceService()

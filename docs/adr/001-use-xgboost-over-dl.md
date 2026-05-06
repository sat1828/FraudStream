# ADR-001: Use XGBoost Over Deep Learning

**Status:** Accepted  
**Date:** 2026-05-02  
**Context:** Fraud detection model selection for real-time UPI transactions

## Decision

We use XGBoost with SHAP TreeExplainer instead of neural networks (LSTM/Transformer).

## Rationale

1. **Training data size**: 100K synthetic records. XGBoost is optimal at this scale; neural networks require millions.
2. **Latency target**: <80ms p95. XGBoost inference is ~2ms vs ~15ms for a small MLP. SHAP TreeExplainer is O(T*D) not O(T*N).
3. **Explainability requirement**: RBI guidelines require per-decision explanations. SHAP gives exact Shapley values.
4. **Retraining speed**: XGBoost from scratch takes ~3 minutes. Incremental NN fine-tuning risks catastrophic forgetting.

## Trade-offs

- Cannot capture complex non-linear temporal patterns that LSTMs handle
- Mitigated by rich feature engineering (20 features with rolling windows up to 24h)

## Alternatives Considered

- Small MLP (1-2 hidden layers) — faster inference but harder to explain
- LightGBM — similar performance, slightly faster training, but SHAP integration is less mature
- TabNet — neural network for tabular data, but needs more data and has higher latency

# ADR-003: Batch Drift Detection Over Online/Streaming Detectors

**Status:** Accepted  
**Date:** 2026-05-02  
**Context:** Concept drift detection approach for production fraud model

## Decision

Run Evidently AI batch drift detection every 500 transactions instead of using online/streaming detectors (ADWIN, Page-Hinkley, DDM).

## Rationale

1. **Statistical significance**: 500-transaction batches give sufficient power for KS tests and PSI calculations (p < 0.05).
2. **False positive rate**: Online detectors have higher false-positive rates at low window sizes, especially for high-dimensional feature spaces.
3. **Operational simplicity**: Batch windows align naturally with Celery task granularity for retraining.

## Trade-offs

- Up to 500 transactions may be scored with a drifted model
- At 20 TPS, worst-case exposure is ~25 seconds
- Acceptable for a demo; production would use shorter windows or online detectors with adaptive thresholds

## Alternatives Considered

- ADWIN — adaptive windowing, but higher false positives
- Page-Hinkley — good for single-feature drift, less so for 20-dimensional spaces
- PSI thresholds per-feature — simpler but less statistically rigorous than Evidently's full test suite

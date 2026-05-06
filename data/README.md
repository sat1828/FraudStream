# /data

This directory is auto-populated by the `data-generator` Docker service on first run.

Contents after startup:
- `train.parquet` — 80k pre-drift training transactions
- `test.parquet` — 20k post-drift transactions (drift detection evaluation)
- `full_dataset.parquet` — complete 100k dataset used for retraining
- `feature_importance.csv` — SHAP feature rankings from last training run
- `classification_report.json` — precision/recall/F1 from last training run
- `drift_reports/` — Evidently HTML drift reports (auto-generated)

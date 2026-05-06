"""Initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-01-01 00:00:00.000000

Note: Admin user is NOT seeded here. Use the /seed-admin endpoint or entrypoint.sh
to create admin users from environment variables.

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("is_superuser", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("transaction_id", sa.String(64), nullable=False, unique=True),
        sa.Column("sender_vpa", sa.String(255), nullable=False),
        sa.Column("receiver_vpa", sa.String(255), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(3), server_default=sa.text("'INR'")),
        sa.Column("device_id", sa.String(255), nullable=True),
        sa.Column("device_os", sa.String(50), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("state", sa.String(100), nullable=True),
        sa.Column("initiated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("is_festival_day", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("festival_name", sa.String(100), nullable=True),
        sa.Column("features", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("decision", sa.String(20), nullable=True),
        sa.Column("is_fraud_actual", sa.Boolean(), nullable=True),
        sa.Column("shap_values", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("rule_triggers", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("explanation_text", sa.Text(), nullable=True),
        sa.Column("model_version", sa.String(50), nullable=True),
        sa.Column("inference_latency_ms", sa.Float(), nullable=True),
    )
    op.create_index("ix_transactions_transaction_id", "transactions", ["transaction_id"])
    op.create_index("ix_transactions_sender_vpa", "transactions", ["sender_vpa"])
    op.create_index("ix_transactions_decision", "transactions", ["decision"])

    op.create_table(
        "model_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("mlflow_run_id", sa.String(64), nullable=False, unique=True),
        sa.Column("mlflow_version", sa.String(20), nullable=True),
        sa.Column("model_name", sa.String(100), server_default=sa.text("'upi-fraud-xgboost'")),
        sa.Column("stage", sa.String(20), server_default=sa.text("'Staging'")),
        sa.Column("train_auc", sa.Float(), nullable=True),
        sa.Column("val_auc", sa.Float(), nullable=True),
        sa.Column("precision", sa.Float(), nullable=True),
        sa.Column("recall", sa.Float(), nullable=True),
        sa.Column("f1_score", sa.Float(), nullable=True),
        sa.Column("fpr", sa.Float(), nullable=True),
        sa.Column("drift_score", sa.Float(), nullable=True),
        sa.Column("triggered_by_drift", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("training_samples", sa.Integer(), nullable=True),
        sa.Column("feature_names", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("false")),
    )

    op.create_table(
        "drift_reports",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("report_id", sa.String(64), nullable=False, unique=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("transaction_count", sa.Integer(), nullable=True),
        sa.Column("dataset_drift_score", sa.Float(), nullable=True),
        sa.Column("prediction_drift_score", sa.Float(), nullable=True),
        sa.Column("n_drifted_features", sa.Integer(), nullable=True),
        sa.Column("drifted_features", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("drift_detected", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("retrain_triggered", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("report_html_path", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource", sa.String(100), nullable=True),
        sa.Column("resource_id", sa.String(64), nullable=True),
        sa.Column("details", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("drift_reports")
    op.drop_table("model_versions")
    op.drop_table("transactions")
    op.drop_table("users")

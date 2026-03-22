"""Initial governed agent schema foundation."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260313_0001"
down_revision = None
branch_labels = None
depends_on = None

run_status = sa.Enum(
    "PENDING",
    "IN_PROGRESS",
    "WAITING_FOR_APPROVAL",
    "COMPLETED",
    "FAILED",
    "CANCELED",
    name="run_status",
    native_enum=False,
)
approval_status = sa.Enum(
    "PENDING",
    "APPROVED",
    "REJECTED",
    "EXPIRED",
    name="approval_status",
    native_enum=False,
)
tool_invocation_status = sa.Enum(
    "PENDING",
    "APPROVAL_REQUIRED",
    "COMPLETED",
    "FAILED",
    "CANCELED",
    name="tool_invocation_status",
    native_enum=False,
)
eval_run_status = sa.Enum(
    "PENDING",
    "IN_PROGRESS",
    "COMPLETED",
    "FAILED",
    name="eval_run_status",
    native_enum=False,
)
eval_result_status = sa.Enum(
    "PASSED",
    "FAILED",
    "ERROR",
    name="eval_result_status",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("status", run_status, nullable=False),
        sa.Column("workflow_key", sa.String(length=100), nullable=False),
        sa.Column("requested_by", sa.String(length=255), nullable=True),
        sa.Column("input_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_runs")),
    )
    op.create_index(op.f("ix_runs_status"), "runs", ["status"], unique=False)

    op.create_table(
        "prompt_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("template_text", sa.Text(), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("prompt_metadata", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prompt_versions")),
        sa.UniqueConstraint("name", "version", name="uq_prompt_versions_name_version"),
    )

    op.create_table(
        "eval_cases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("expected_behavior", sa.Text(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_eval_cases")),
        sa.UniqueConstraint("key", name=op.f("uq_eval_cases_key")),
    )

    op.create_table(
        "eval_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("status", eval_run_status, nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_eval_runs")),
    )
    op.create_index(op.f("ix_eval_runs_status"), "eval_runs", ["status"], unique=False)

    op.create_table(
        "run_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], name=op.f("fk_run_events_run_id_runs"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_run_events")),
        sa.UniqueConstraint("run_id", "sequence", name="uq_run_events_run_id_sequence"),
    )
    op.create_index(op.f("ix_run_events_run_id"), "run_events", ["run_id"], unique=False)

    op.create_table(
        "tool_invocations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("tool_name", sa.String(length=100), nullable=False),
        sa.Column("status", tool_invocation_status, nullable=False),
        sa.Column("requires_approval", sa.Boolean(), nullable=False),
        sa.Column("input_payload", sa.JSON(), nullable=True),
        sa.Column("output_payload", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], name=op.f("fk_tool_invocations_run_id_runs"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tool_invocations")),
    )
    op.create_index(op.f("ix_tool_invocations_run_id"), "tool_invocations", ["run_id"], unique=False)

    op.create_table(
        "approval_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("tool_invocation_id", sa.Uuid(), nullable=True),
        sa.Column("status", approval_status, nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("action_preview", sa.JSON(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decision_comment", sa.String(length=500), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], name=op.f("fk_approval_requests_run_id_runs"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tool_invocation_id"], ["tool_invocations.id"], name=op.f("fk_approval_requests_tool_invocation_id_tool_invocations"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_approval_requests")),
        sa.UniqueConstraint("tool_invocation_id", name="uq_approval_requests_tool_invocation_id"),
    )
    op.create_index(op.f("ix_approval_requests_run_id"), "approval_requests", ["run_id"], unique=False)
    op.create_index(op.f("ix_approval_requests_status"), "approval_requests", ["status"], unique=False)

    op.create_table(
        "eval_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("eval_run_id", sa.Uuid(), nullable=False),
        sa.Column("eval_case_id", sa.Uuid(), nullable=False),
        sa.Column("status", eval_result_status, nullable=False),
        sa.Column("score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("summary", sa.String(length=500), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["eval_case_id"], ["eval_cases.id"], name=op.f("fk_eval_results_eval_case_id_eval_cases"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["eval_run_id"], ["eval_runs.id"], name=op.f("fk_eval_results_eval_run_id_eval_runs"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_eval_results")),
        sa.UniqueConstraint("eval_run_id", "eval_case_id", name="uq_eval_results_run_case"),
    )
    op.create_index(op.f("ix_eval_results_eval_run_id"), "eval_results", ["eval_run_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_eval_results_eval_run_id"), table_name="eval_results")
    op.drop_table("eval_results")
    op.drop_index(op.f("ix_approval_requests_status"), table_name="approval_requests")
    op.drop_index(op.f("ix_approval_requests_run_id"), table_name="approval_requests")
    op.drop_table("approval_requests")
    op.drop_index(op.f("ix_tool_invocations_run_id"), table_name="tool_invocations")
    op.drop_table("tool_invocations")
    op.drop_index(op.f("ix_run_events_run_id"), table_name="run_events")
    op.drop_table("run_events")
    op.drop_index(op.f("ix_eval_runs_status"), table_name="eval_runs")
    op.drop_table("eval_runs")
    op.drop_table("eval_cases")
    op.drop_table("prompt_versions")
    op.drop_index(op.f("ix_runs_status"), table_name="runs")
    op.drop_table("runs")

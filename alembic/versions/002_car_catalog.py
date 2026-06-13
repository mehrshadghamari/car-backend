"""car catalog and purchase request filters

Revision ID: 002
Revises: 001
Create Date: 2026-06-05

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "car_brands",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "car_models",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("car_brands.id"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("slug", sa.String(150), nullable=False, unique=True),
        sa.Column("divar_path", sa.String(300), nullable=False),
        sa.Column("divar_brand_model", sa.String(200), nullable=False),
        sa.Column("hamrah_brand", sa.String(100), nullable=False),
        sa.Column("hamrah_model", sa.String(100), nullable=False),
        sa.Column("hamrah_type_id", sa.String(20), nullable=False),
        sa.Column("default_color", sa.String(50), server_default="ColorWhite"),
        sa.Column("default_body_condition", sa.String(50), server_default="WithoutColor"),
        sa.Column("color_map", postgresql.JSONB()),
        sa.Column("near_threshold_pct", sa.Numeric(5, 4), server_default="0.02"),
        sa.Column("max_pages_per_run", sa.Integer(), server_default="5"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_car_models_brand_id", "car_models", ["brand_id"])

    op.add_column("purchase_requests", sa.Column("car_model_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("purchase_requests", sa.Column("city", sa.String(50), server_default="tehran"))
    op.add_column("purchase_requests", sa.Column("production_year_min", sa.Integer()))
    op.add_column("purchase_requests", sa.Column("production_year_max", sa.Integer()))
    op.add_column("purchase_requests", sa.Column("usage_min", sa.Integer()))
    op.add_column("purchase_requests", sa.Column("usage_max", sa.Integer()))
    op.add_column("purchase_requests", sa.Column("generated_divar_url", sa.Text()))
    op.alter_column("purchase_requests", "crawl_target_id", existing_type=postgresql.UUID(), nullable=True)
    op.create_foreign_key(
        "fk_purchase_requests_car_model_id",
        "purchase_requests",
        "car_models",
        ["car_model_id"],
        ["id"],
    )
    op.create_index("ix_purchase_requests_car_model_id", "purchase_requests", ["car_model_id"])


def downgrade() -> None:
    op.drop_index("ix_purchase_requests_car_model_id", "purchase_requests")
    op.drop_constraint("fk_purchase_requests_car_model_id", "purchase_requests", type_="foreignkey")
    op.drop_column("purchase_requests", "generated_divar_url")
    op.drop_column("purchase_requests", "usage_max")
    op.drop_column("purchase_requests", "usage_min")
    op.drop_column("purchase_requests", "production_year_max")
    op.drop_column("purchase_requests", "production_year_min")
    op.drop_column("purchase_requests", "city")
    op.drop_column("purchase_requests", "car_model_id")
    op.alter_column("purchase_requests", "crawl_target_id", existing_type=postgresql.UUID(), nullable=False)
    op.drop_index("ix_car_models_brand_id", "car_models")
    op.drop_table("car_models")
    op.drop_table("car_brands")

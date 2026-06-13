"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-05

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("phone", sa.String(20), nullable=False, unique=True),
        sa.Column("first_name", sa.String(100)),
        sa.Column("last_name", sa.String(100)),
        sa.Column("source_channel", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_phone", "users", ["phone"])

    op.create_table(
        "crawl_targets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("listing_url", sa.Text(), nullable=False),
        sa.Column("vehicle_context", postgresql.JSONB(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("poll_interval_sec", sa.Integer(), server_default="300"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "purchase_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "crawl_target_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("crawl_targets.id"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("near_threshold_pct", sa.Numeric(5, 4)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_purchase_requests_user_id", "purchase_requests", ["user_id"])
    op.create_index("ix_purchase_requests_crawl_target_id", "purchase_requests", ["crawl_target_id"])

    op.create_table(
        "crawl_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "crawl_target_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("crawl_targets.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("posts_found", sa.Integer(), server_default="0"),
        sa.Column("opportunities_found", sa.Integer(), server_default="0"),
        sa.Column("error_message", sa.Text()),
    )
    op.create_index("ix_crawl_runs_crawl_target_id", "crawl_runs", ["crawl_target_id"])

    op.create_table(
        "listings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "crawl_target_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("crawl_targets.id"),
            nullable=False,
        ),
        sa.Column("external_token", sa.String(50), nullable=False, unique=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("price", sa.BigInteger(), nullable=False),
        sa.Column("kilometer", sa.Integer()),
        sa.Column("production_year", sa.Integer()),
        sa.Column("color", sa.String(100)),
        sa.Column("body_condition", sa.String(100)),
        sa.Column("district", sa.String(200)),
        sa.Column("divar_url", sa.Text(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_listings_crawl_target_id", "listings", ["crawl_target_id"])
    op.create_index("ix_listings_external_token", "listings", ["external_token"])

    op.create_table(
        "market_prices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("listings.id"), nullable=False),
        sa.Column("price_up", sa.BigInteger(), nullable=False),
        sa.Column("price_down", sa.BigInteger(), nullable=False),
        sa.Column("price_mid", sa.BigInteger(), nullable=False),
        sa.Column("hamrah_url", sa.Text(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_market_prices_listing_id", "market_prices", ["listing_id"])

    op.create_table(
        "opportunities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("listings.id"), nullable=False),
        sa.Column(
            "crawl_target_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("crawl_targets.id"),
            nullable=False,
        ),
        sa.Column("listing_price", sa.BigInteger(), nullable=False),
        sa.Column("market_price_down", sa.BigInteger(), nullable=False),
        sa.Column("market_price_up", sa.BigInteger(), nullable=False),
        sa.Column("discount_amount", sa.BigInteger(), nullable=False),
        sa.Column("discount_pct", sa.Numeric(8, 2), nullable=False),
        sa.Column("score", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("is_below_floor", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_opportunities_listing_id", "opportunities", ["listing_id"])
    op.create_index("ix_opportunities_crawl_target_id", "opportunities", ["crawl_target_id"])

    op.create_table(
        "opportunity_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "opportunity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("opportunities.id"),
            nullable=False,
        ),
        sa.Column(
            "purchase_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("purchase_requests.id"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("gateway_token", sa.String(64), nullable=False, unique=True),
        sa.Column("sms_status", sa.String(20), server_default="pending"),
        sa.Column("sms_sent_at", sa.DateTime(timezone=True)),
        sa.Column("sms_provider_id", sa.String(100)),
        sa.Column("sms_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_opportunity_deliveries_opportunity_id", "opportunity_deliveries", ["opportunity_id"])
    op.create_index("ix_opportunity_deliveries_gateway_token", "opportunity_deliveries", ["gateway_token"])

    op.create_table(
        "gateway_clicks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "delivery_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("opportunity_deliveries.id"),
            nullable=False,
        ),
        sa.Column("clicked_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("time_to_click_sec", sa.Integer()),
    )
    op.create_index("ix_gateway_clicks_delivery_id", "gateway_clicks", ["delivery_id"])


def downgrade() -> None:
    op.drop_table("gateway_clicks")
    op.drop_table("opportunity_deliveries")
    op.drop_table("opportunities")
    op.drop_table("market_prices")
    op.drop_table("listings")
    op.drop_table("crawl_runs")
    op.drop_table("purchase_requests")
    op.drop_table("crawl_targets")
    op.drop_table("users")

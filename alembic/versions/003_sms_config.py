"""SMS providers and action templates (DB-driven config)

Revision ID: 003
Revises: 002
Create Date: 2026-06-16

"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_PROVIDER_DRY_RUN = uuid.UUID("a1000001-0001-4001-8001-000000000001")
_PROVIDER_SMS_IR = uuid.UUID("a1000001-0001-4001-8001-000000000002")
_PROVIDER_SMS_WS = uuid.UUID("a1000001-0001-4001-8001-000000000003")

_GATEWAY_TEMPLATE = (
    "{discount_label} زیر قیمت بازار {title} قیمت : {price} تومان  "
    "مشاهده آگهی در دیوار : {gateway_url}"
)


def upgrade() -> None:
    op.create_table(
        "sms_providers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("driver", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "sms_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("action", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("send_mode", sa.String(20), nullable=False, server_default="text"),
        sa.Column("text_body", sa.Text()),
        sa.Column("pattern_key", sa.String(120)),
        sa.Column("pattern_slots", postgresql.JSONB()),
        sa.Column("pattern_params", postgresql.JSONB()),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sms_providers.id"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_sms_templates_action", "sms_templates", ["action"])

    providers = sa.table(
        "sms_providers",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("slug", sa.String),
        sa.column("name", sa.String),
        sa.column("driver", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("config", postgresql.JSONB),
    )
    templates = sa.table(
        "sms_templates",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("action", sa.String),
        sa.column("name", sa.String),
        sa.column("send_mode", sa.String),
        sa.column("text_body", sa.Text),
        sa.column("pattern_key", sa.String),
        sa.column("pattern_slots", postgresql.JSONB),
        sa.column("pattern_params", postgresql.JSONB),
        sa.column("provider_id", postgresql.UUID(as_uuid=True)),
        sa.column("is_active", sa.Boolean),
    )

    op.bulk_insert(
        providers,
        [
            {
                "id": _PROVIDER_DRY_RUN,
                "slug": "dry_run",
                "name": "Dry run (no SMS)",
                "driver": "dry_run",
                "is_active": True,
                "config": {},
            },
            {
                "id": _PROVIDER_SMS_IR,
                "slug": "sms_ir",
                "name": "SMS.ir",
                "driver": "sms_ir",
                "is_active": True,
                "config": {
                    "api_key": "",
                    "line_number": "",
                    "base_url": "https://api.sms.ir/v1",
                    "template_id": "",
                },
            },
            {
                "id": _PROVIDER_SMS_WS,
                "slug": "sms_webservice",
                "name": "SMS WebService",
                "driver": "sms_webservice",
                "is_active": True,
                "config": {
                    "api_key": "",
                    "sender": "",
                    "base_url": "https://api.sms-webservice.com/api/V3",
                },
            },
        ],
    )

    op.bulk_insert(
        templates,
        [
            {
                "id": uuid.uuid4(),
                "action": "gateway_link",
                "name": "Gateway opportunity link",
                "send_mode": "text",
                "text_body": _GATEWAY_TEMPLATE,
                "pattern_key": None,
                "pattern_slots": ["discount_label", "title", "price_and_gateway"],
                "pattern_params": ["discount_label", "title", "price", "gateway_url"],
                "provider_id": _PROVIDER_DRY_RUN,
                "is_active": True,
            },
            {
                "id": uuid.uuid4(),
                "action": "otp_code",
                "name": "OTP login code",
                "send_mode": "text",
                "text_body": "کد ورود شما: {code}",
                "pattern_key": None,
                "pattern_slots": None,
                "pattern_params": ["code"],
                "provider_id": _PROVIDER_DRY_RUN,
                "is_active": True,
            },
            {
                "id": uuid.uuid4(),
                "action": "portal_link",
                "name": "Portal share link",
                "send_mode": "text",
                "text_body": "فرصت‌های خرید خودرو برای شما:\n{share_url}",
                "pattern_key": None,
                "pattern_slots": None,
                "pattern_params": ["share_url"],
                "provider_id": _PROVIDER_DRY_RUN,
                "is_active": True,
            },
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_sms_templates_action", table_name="sms_templates")
    op.drop_table("sms_templates")
    op.drop_table("sms_providers")

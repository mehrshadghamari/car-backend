"""Seed or update SMS providers and action templates in the database.

Idempotent — safe to run multiple times. Updates provider config and template rows.

Usage (from project root):
  python3 scripts/seed_sms_config.py

With credentials via environment:
  SMS_WEBSERVICE_API_KEY=... SMS_WEBSERVICE_SENDER=... python3 scripts/seed_sms_config.py

Or use the wrapper (loads scripts/deploy/sms.seed.env if present):
  bash scripts/run_seed_sms_config.sh
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from src.infrastructure.persistence.database import async_session_factory
from src.infrastructure.persistence.models import SmsProviderModel, SmsTemplateModel
from src.infrastructure.persistence.sms_defaults import (
    GATEWAY_PATTERN_PARAMS,
    GATEWAY_PATTERN_SLOTS,
    GATEWAY_TEXT_TEMPLATE,
    OTP_TEXT_TEMPLATE,
    PORTAL_TEXT_TEMPLATE,
    PROVIDER_DRY_RUN_ID,
    PROVIDER_SMS_IR_ID,
    PROVIDER_SMS_WEBSERVICE_ID,
    SMS_IR_BASE_URL,
    SMS_WEBSERVICE_BASE_URL,
)


def _webservice_config(api_key: str, sender: str) -> dict:
    return {
        "api_key": api_key,
        "sender": sender,
        "base_url": SMS_WEBSERVICE_BASE_URL,
    }


def _provider_rows(api_key: str, sender: str) -> list[dict]:
    return [
        {
            "id": PROVIDER_DRY_RUN_ID,
            "slug": "dry_run",
            "name": "Dry run (no SMS)",
            "driver": "dry_run",
            "is_active": True,
            "config": {},
        },
        {
            "id": PROVIDER_SMS_IR_ID,
            "slug": "sms_ir",
            "name": "SMS.ir",
            "driver": "sms_ir",
            "is_active": True,
            "config": {
                "api_key": "",
                "line_number": "",
                "base_url": SMS_IR_BASE_URL,
                "template_id": "",
            },
        },
        {
            "id": PROVIDER_SMS_WEBSERVICE_ID,
            "slug": "sms_webservice",
            "name": "SMS WebService",
            "driver": "sms_webservice",
            "is_active": bool(api_key),
            "config": _webservice_config(api_key, sender),
        },
    ]


def _template_rows(provider_id: uuid.UUID) -> list[dict]:
    return [
        {
            "action": "gateway_link",
            "name": "Gateway opportunity link",
            "send_mode": "text",
            "text_body": GATEWAY_TEXT_TEMPLATE,
            "pattern_key": None,
            "pattern_slots": GATEWAY_PATTERN_SLOTS,
            "pattern_params": GATEWAY_PATTERN_PARAMS,
            "provider_id": provider_id,
            "is_active": True,
        },
        {
            "action": "otp_code",
            "name": "OTP login code",
            "send_mode": "text",
            "text_body": OTP_TEXT_TEMPLATE,
            "pattern_key": None,
            "pattern_slots": None,
            "pattern_params": ["code"],
            "provider_id": provider_id,
            "is_active": True,
        },
        {
            "action": "portal_link",
            "name": "Portal share link",
            "send_mode": "text",
            "text_body": PORTAL_TEXT_TEMPLATE,
            "pattern_key": None,
            "pattern_slots": None,
            "pattern_params": ["share_url"],
            "provider_id": provider_id,
            "is_active": True,
        },
    ]


async def seed_sms_config(api_key: str, sender: str) -> None:
    use_webservice = bool(api_key.strip())
    default_provider_id = PROVIDER_SMS_WEBSERVICE_ID if use_webservice else PROVIDER_DRY_RUN_ID

    async with async_session_factory() as session:
        for row in _provider_rows(api_key.strip(), sender.strip()):
            existing = await session.execute(
                select(SmsProviderModel).where(SmsProviderModel.slug == row["slug"])
            )
            model = existing.scalar_one_or_none()
            if model:
                model.name = row["name"]
                model.driver = row["driver"]
                model.is_active = row["is_active"]
                model.config = row["config"]
            else:
                session.add(SmsProviderModel(**row))

        for row in _template_rows(default_provider_id):
            existing = await session.execute(
                select(SmsTemplateModel).where(SmsTemplateModel.action == row["action"])
            )
            model = existing.scalar_one_or_none()
            if model:
                model.name = row["name"]
                model.send_mode = row["send_mode"]
                model.text_body = row["text_body"]
                model.pattern_key = row["pattern_key"]
                model.pattern_slots = row["pattern_slots"]
                model.pattern_params = row["pattern_params"]
                model.provider_id = row["provider_id"]
                model.is_active = row["is_active"]
            else:
                session.add(SmsTemplateModel(id=uuid.uuid4(), **row))

        await session.commit()

    provider_label = "sms_webservice" if use_webservice else "dry_run"
    print(f"SMS config seeded — templates use provider: {provider_label}")
    if use_webservice:
        sender_note = sender.strip() or "(no sender)"
        print(f"  SMS WebService sender: {sender_note}")
        print(f"  API key: {'*' * 8}{api_key.strip()[-6:]}")
    else:
        print("  Warning: SMS_WEBSERVICE_API_KEY not set — using dry_run (no real SMS).")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed SMS providers and templates")
    parser.add_argument(
        "--api-key",
        default=os.environ.get("SMS_WEBSERVICE_API_KEY", ""),
        help="SMS WebService API key (or SMS_WEBSERVICE_API_KEY env)",
    )
    parser.add_argument(
        "--sender",
        default=os.environ.get("SMS_WEBSERVICE_SENDER", ""),
        help="SMS WebService sender line (or SMS_WEBSERVICE_SENDER env)",
    )
    args = parser.parse_args()
    asyncio.run(seed_sms_config(args.api_key, args.sender))


if __name__ == "__main__":
    main()

"""Seed listing/pricing platforms. Car catalog comes from Khodro45 import."""
import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from src.infrastructure.persistence.database import async_session_factory
from src.infrastructure.persistence.models import ListingPlatformModel, PricingPlatformModel


async def seed():
    async with async_session_factory() as session:
        existing = await session.execute(select(ListingPlatformModel).limit(1))
        if existing.scalar_one_or_none():
            print("Platforms already seeded, skipping.")
            return

        session.add(
            ListingPlatformModel(
                id=uuid.uuid4(),
                slug="divar",
                name="دیوار",
                fetch_strategy="api",
                is_active=True,
            )
        )
        session.add(
            PricingPlatformModel(
                id=uuid.uuid4(),
                slug="hamrah_mechanic",
                name="همراه مکانیک",
                fetch_strategy="crawl",
                is_active=True,
            )
        )
        session.add(
            PricingPlatformModel(
                id=uuid.uuid4(),
                slug="khodro45",
                name="خودرو۴۵",
                fetch_strategy="crawl",
                is_active=True,
            )
        )

        await session.commit()
        print("Seeded listing/pricing platforms (divar, hamrah_mechanic, khodro45).")


if __name__ == "__main__":
    asyncio.run(seed())

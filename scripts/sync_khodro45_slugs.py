"""Sync Khodro45 slug in mapping config JSON and crawl target vehicle_context."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from src.application.services.pricing_config_builder import merge_khodro45_pricing_config
from src.domain.entities.crawl_target import VehicleContext
from src.infrastructure.persistence.database import async_session_factory
from src.infrastructure.persistence.models import (
    CarModelPricingMappingModel,
    CrawlTargetModel,
    PricingPlatformModel,
    PurchaseRequestCrawlTargetModel,
    PurchaseRequestModel,
)
from src.infrastructure.persistence.platform_repositories import SqlAlchemyPlatformRepository
from src.infrastructure.persistence.repositories import SqlAlchemyCrawlTargetRepository


async def sync() -> None:
    mapping_updates = 0
    target_updates = 0

    async with async_session_factory() as session:
        platform_repo = SqlAlchemyPlatformRepository(session)
        crawl_repo = SqlAlchemyCrawlTargetRepository(session)

        khodro45 = await platform_repo.get_pricing_platform_by_slug("khodro45")
        if not khodro45:
            print("Khodro45 platform not found — nothing to sync.")
            return

        result = await session.execute(
            select(CarModelPricingMappingModel).where(
                CarModelPricingMappingModel.pricing_platform_id == khodro45.id,
                CarModelPricingMappingModel.is_active.is_(True),
            )
        )
        for model in result.scalars().all():
            config = dict(model.config or {})
            if config.get("slug") == model.slug:
                continue
            config["slug"] = model.slug
            model.config = config
            mapping_updates += 1
            print(f"Mapping {model.id}: config slug -> {model.slug}")

        targets = await session.execute(select(CrawlTargetModel))
        for target_model in targets.scalars().all():
            ctx = VehicleContext.from_dict(target_model.vehicle_context or {})
            if ctx.pricing_platform != "khodro45":
                continue

            purchase = await session.execute(
                select(PurchaseRequestModel)
                .outerjoin(
                    PurchaseRequestCrawlTargetModel,
                    PurchaseRequestCrawlTargetModel.purchase_request_id == PurchaseRequestModel.id,
                )
                .where(
                    PurchaseRequestModel.is_active.is_(True),
                    (
                        (PurchaseRequestModel.crawl_target_id == target_model.id)
                        | (PurchaseRequestCrawlTargetModel.crawl_target_id == target_model.id)
                    ),
                )
                .limit(1)
            )
            pr = purchase.scalar_one_or_none()
            if not pr:
                continue

            mapping = await platform_repo.get_pricing_mapping(pr.car_model_id, khodro45.id)
            if not mapping:
                continue

            fresh = merge_khodro45_pricing_config(mapping, existing=ctx.pricing_config)
            if fresh.get("slug") == (ctx.pricing_config or {}).get("slug"):
                continue

            ctx.pricing_config = fresh
            target_model.vehicle_context = ctx.to_dict()
            target_updates += 1
            print(
                f"Crawl target {target_model.id}: pricing_config slug -> {fresh.get('slug')}"
            )

        await session.commit()

    print(f"Done — updated {mapping_updates} mapping(s), {target_updates} crawl target(s).")


if __name__ == "__main__":
    asyncio.run(sync())

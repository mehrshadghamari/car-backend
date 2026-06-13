"""Merge duplicate shared crawl pools created before unique-pool enforcement."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select, update

from src.infrastructure.persistence.database import async_session_factory
from src.infrastructure.persistence.models import (
    CrawlTargetModel,
    PurchaseRequestCrawlTargetModel,
    PurchaseRequestModel,
)


async def dedupe() -> None:
    async with async_session_factory() as session:
        groups = await session.execute(
            select(
                CrawlTargetModel.listing_mapping_id,
                CrawlTargetModel.city,
                CrawlTargetModel.source,
                CrawlTargetModel.pool_production_year,
                func.count(),
            )
            .where(
                CrawlTargetModel.is_shared_pool.is_(True),
                CrawlTargetModel.listing_mapping_id.is_not(None),
            )
            .group_by(
                CrawlTargetModel.listing_mapping_id,
                CrawlTargetModel.city,
                CrawlTargetModel.source,
                CrawlTargetModel.pool_production_year,
            )
            .having(func.count() > 1)
        )
        duplicate_groups = groups.all()
        if not duplicate_groups:
            print("No duplicate shared pools found.")
            return

        merged = 0
        for listing_mapping_id, city, source, pool_year, _count in duplicate_groups:
            result = await session.execute(
                select(CrawlTargetModel)
                .where(
                    CrawlTargetModel.listing_mapping_id == listing_mapping_id,
                    CrawlTargetModel.city == city,
                    CrawlTargetModel.source == source,
                    CrawlTargetModel.is_shared_pool.is_(True),
                    CrawlTargetModel.pool_production_year == pool_year
                    if pool_year is not None
                    else CrawlTargetModel.pool_production_year.is_(None),
                )
                .order_by(
                    CrawlTargetModel.is_active.desc(),
                    CrawlTargetModel.updated_at.desc(),
                    CrawlTargetModel.created_at.desc(),
                )
            )
            pools = list(result.scalars().all())
            if len(pools) < 2:
                continue

            keep = pools[0]
            drop_ids = [p.id for p in pools[1:]]

            await session.execute(
                update(PurchaseRequestModel)
                .where(PurchaseRequestModel.crawl_target_id.in_(drop_ids))
                .values(crawl_target_id=keep.id)
            )
            await session.execute(
                update(PurchaseRequestCrawlTargetModel)
                .where(PurchaseRequestCrawlTargetModel.crawl_target_id.in_(drop_ids))
                .values(crawl_target_id=keep.id)
            )
            await session.execute(
                update(CrawlTargetModel)
                .where(CrawlTargetModel.id.in_(drop_ids))
                .values(is_active=False)
            )
            merged += len(drop_ids)
            print(
                f"Kept pool {keep.id} for listing_mapping={listing_mapping_id} {city}/{source}; "
                f"deactivated {len(drop_ids)} duplicate(s)"
            )

        await session.commit()
        print(f"Deduped {merged} duplicate shared pool(s).")


if __name__ == "__main__":
    asyncio.run(dedupe())

"""Expire invalid Khodro45 opportunities and refresh discount vs ceiling (max)."""
import asyncio
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from src.application.mappers.entity_mappers import opportunity_to_domain
from src.domain.entities.opportunity import OpportunityStatus
from src.domain.services.opportunity_scorer import evaluate_urgent_sale_opportunity
from src.infrastructure.persistence.database import async_session_factory
from src.infrastructure.persistence.models import ListingModel, MarketPriceModel, OpportunityModel
from src.infrastructure.persistence.repositories import SqlAlchemyOpportunityRepository


async def revalidate() -> None:
    expired = 0
    refreshed = 0
    deduped = 0

    async with async_session_factory() as session:
        repo = SqlAlchemyOpportunityRepository(session)
        result = await session.execute(
            select(OpportunityModel).where(OpportunityModel.status != "expired")
        )
        active = result.scalars().all()
        by_listing: dict = defaultdict(list)
        for model in active:
            by_listing[model.listing_id].append(model)

        for listing_id, models in by_listing.items():
            listing = await session.get(ListingModel, listing_id)
            if listing is None:
                for model in models:
                    opp = opportunity_to_domain(model)
                    opp.status = OpportunityStatus.EXPIRED
                    await repo.save(opp)
                    expired += 1
                continue

            mp_result = await session.execute(
                select(MarketPriceModel)
                .where(MarketPriceModel.listing_id == listing_id)
                .order_by(MarketPriceModel.fetched_at.desc())
                .limit(1)
            )
            mp = mp_result.scalar_one_or_none()
            if mp is None:
                continue

            tier_matches = evaluate_urgent_sale_opportunity(
                listing.price,
                mp.price_down,
                mp.price_mid,
                mp.price_up,
            )
            if not tier_matches:
                for model in models:
                    opp = opportunity_to_domain(model)
                    opp.status = OpportunityStatus.EXPIRED
                    await repo.save(opp)
                    expired += 1
                continue

            match = tier_matches[0]
            keeper = max(models, key=lambda m: m.created_at)
            opp = opportunity_to_domain(keeper)
            opp.listing_price = listing.price
            opp.market_price_down = mp.price_down
            opp.market_price_up = mp.price_up
            opp.market_price_mid = mp.price_mid
            opp.price_basis = match.basis
            opp.deal_tag = match.deal_tag
            opp.reference_price = match.reference_price
            opp.discount_amount = match.discount_amount
            opp.discount_pct = match.discount_pct
            opp.score = match.score
            opp.is_below_floor = match.is_below
            opp.crawl_target_id = listing.crawl_target_id
            await repo.save(opp)
            refreshed += 1

            for model in models:
                if model.id == keeper.id:
                    continue
                extra = opportunity_to_domain(model)
                extra.status = OpportunityStatus.EXPIRED
                await repo.save(extra)
                deduped += 1

    print(f"Done — refreshed {refreshed}, expired {expired}, deduped {deduped}.")


if __name__ == "__main__":
    asyncio.run(revalidate())

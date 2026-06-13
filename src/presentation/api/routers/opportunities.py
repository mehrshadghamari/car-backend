from uuid import UUID

from fastapi import APIRouter, Depends

from src.presentation.api.schemas import OpportunityResponse
from src.presentation.dependencies import get_opportunity_repo

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.get("", response_model=list[OpportunityResponse])
async def list_opportunities(
    crawl_target_id: UUID | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 100,
    opportunity_repo=Depends(get_opportunity_repo),
):
    opportunities = await opportunity_repo.list_all(
        crawl_target_id=crawl_target_id,
        status=status,
        skip=skip,
        limit=limit,
    )
    return [
        OpportunityResponse(
            id=o.id,
            listing_id=o.listing_id,
            crawl_target_id=o.crawl_target_id,
            listing_price=o.listing_price,
            market_price_down=o.market_price_down,
            market_price_up=o.market_price_up,
            market_price_mid=o.market_price_mid,
            price_basis=o.price_basis,
            deal_tag=o.deal_tag,
            reference_price=o.reference_price or o.market_price_down,
            discount_amount=o.discount_amount,
            discount_pct=o.discount_pct,
            score=o.score,
            status=o.status.value,
            is_below_floor=o.is_below_floor,
            created_at=o.created_at,
        )
        for o in opportunities
    ]

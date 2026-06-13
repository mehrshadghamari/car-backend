from fastapi import APIRouter, Depends

from src.presentation.api.schemas import PlatformResponse
from src.presentation.dependencies import get_platform_repo

router = APIRouter(tags=["platforms"])


@router.get("/listing-platforms", response_model=list[PlatformResponse])
async def list_listing_platforms(repo=Depends(get_platform_repo)):
    platforms = await repo.list_listing_platforms(active_only=True)
    return [
        PlatformResponse(
            id=p.id, slug=p.slug, name=p.name, fetch_strategy=p.fetch_strategy, is_active=p.is_active
        )
        for p in platforms
    ]


@router.get("/pricing-platforms", response_model=list[PlatformResponse])
async def list_pricing_platforms(repo=Depends(get_platform_repo)):
    platforms = await repo.list_pricing_platforms(active_only=True)
    return [
        PlatformResponse(
            id=p.id, slug=p.slug, name=p.name, fetch_strategy=p.fetch_strategy, is_active=p.is_active
        )
        for p in platforms
    ]

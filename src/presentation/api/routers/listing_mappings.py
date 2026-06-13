from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException

from src.domain.entities.platform import ListingMapping
from src.presentation.api.schemas import (
    ListingMappingCreate,
    ListingMappingLinkTrims,
    ListingMappingResponse,
)
from src.presentation.dependencies import get_platform_repo

router = APIRouter(tags=["listing-mappings"])


@router.get("/listing-mappings", response_model=list[ListingMappingResponse])
async def list_listing_mappings(
    model_id: UUID | None = None,
    repo=Depends(get_platform_repo),
):
    rows = await repo.list_listing_mappings(model_id=model_id)
    return [ListingMappingResponse(**row) for row in rows]


@router.post("/listing-mappings", response_model=ListingMappingResponse, status_code=201)
async def create_listing_mapping(body: ListingMappingCreate, repo=Depends(get_platform_repo)):
    platform = await repo.get_listing_platform_by_slug(body.listing_platform_slug)
    if not platform:
        raise HTTPException(status_code=404, detail="پلتفرم آگهی پیدا نشد")
    divar_model = await repo.get_divar_car_model_by_id(body.divar_car_model_id)
    if not divar_model:
        raise HTTPException(status_code=404, detail="مدل دیوار پیدا نشد")
    mapping = ListingMapping(
        id=uuid4(),
        listing_platform_id=platform.id,
        divar_car_model_id=body.divar_car_model_id,
        path=body.path.strip(),
        divar_brand_model=divar_model.slug,
        config=body.config,
        is_active=True,
        trim_ids=[],
    )
    saved = await repo.create_listing_mapping(mapping)
    for trim_id in body.trim_ids:
        await repo.link_trim_to_listing_mapping(trim_id, saved.id)
    await repo.commit()
    return ListingMappingResponse(
        id=saved.id,
        listing_platform_slug=body.listing_platform_slug,
        path=saved.path,
        divar_car_model_id=saved.divar_car_model_id,
        divar_car_model_slug=divar_model.slug,
        divar_car_model_display=divar_model.display,
        is_active=True,
        trim_count=len(body.trim_ids),
        trims=[],
    )


@router.post("/listing-mappings/{mapping_id}/trims", status_code=204)
async def link_trims_to_mapping(
    mapping_id: UUID,
    body: ListingMappingLinkTrims,
    repo=Depends(get_platform_repo),
):
    mapping = await repo.get_listing_mapping_by_id(mapping_id)
    if not mapping:
        raise HTTPException(status_code=404, detail="نگاشت پیدا نشد")
    for trim_id in body.trim_ids:
        await repo.link_trim_to_listing_mapping(trim_id, mapping_id)
    await repo.commit()

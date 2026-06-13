from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from src.application.ports.car_catalog import (
    CarBrandRepository,
    CarModelRepository,
    CarTrimRepository,
    CarYearRepository,
)
from src.domain.exceptions import EntityNotFoundError
from src.presentation.api.schemas import (
    CarBrandResponse,
    CarModelResponse,
    CarTrimResponse,
    CarYearResponse,
    PreviewUrlsRequest,
    PreviewUrlsResponse,
    PurchaseFlowCreate,
    PurchaseFlowResponse,
)
from src.presentation.dependencies import (
    get_car_brand_repo,
    get_car_model_repo,
    get_car_trim_repo,
    get_car_year_repo,
    get_create_purchase_flow_use_case,
    get_preview_urls_use_case,
)

router = APIRouter(tags=["car-catalog"])


@router.get("/car-brands", response_model=list[CarBrandResponse])
async def list_car_brands(
    active_only: bool = True,
    repo: CarBrandRepository = Depends(get_car_brand_repo),
):
    brands = await repo.list_all(active_only=active_only)
    return [CarBrandResponse(id=b.id, name=b.name, slug=b.slug, is_active=b.is_active) for b in brands]


@router.get("/car-models", response_model=list[CarModelResponse])
async def list_car_models(
    brand_id: UUID | None = None,
    active_only: bool = True,
    repo: CarModelRepository = Depends(get_car_model_repo),
):
    models = await repo.list_all(brand_id=brand_id, active_only=active_only)
    return [
        CarModelResponse(
            id=m.id,
            brand_id=m.brand_id,
            brand_name=m.brand_name,
            name=m.name,
            slug=m.slug,
            is_active=m.is_active,
        )
        for m in models
    ]


@router.get("/car-years", response_model=list[CarYearResponse])
async def list_car_years(
    model_id: UUID,
    active_only: bool = True,
    repo: CarYearRepository = Depends(get_car_year_repo),
):
    years = await repo.list_by_model(model_id, active_only=active_only)
    return [
        CarYearResponse(
            id=y.id,
            model_id=y.model_id,
            title=y.title,
            model_name=y.model_name,
            brand_name=y.brand_name,
            is_active=y.is_active,
        )
        for y in years
    ]


@router.get("/car-trims", response_model=list[CarTrimResponse])
async def list_car_trims(
    model_id: UUID,
    year_id: UUID | None = None,
    active_only: bool = True,
    repo: CarTrimRepository = Depends(get_car_trim_repo),
):
    trims = await repo.list_by_model(model_id, year_id=year_id, active_only=active_only)
    return [
        CarTrimResponse(
            id=t.id,
            model_id=t.model_id,
            year_id=t.year_id,
            name=t.name,
            seo_slug=t.seo_slug,
            year_title=t.year_title,
            model_name=t.model_name,
            brand_name=t.brand_name,
            is_active=t.is_active,
        )
        for t in trims
    ]


@router.post("/preview-urls", response_model=PreviewUrlsResponse)
async def preview_urls(
    body: PreviewUrlsRequest,
    use_case=Depends(get_preview_urls_use_case),
):
    from src.application.use_cases.preview_urls import PreviewUrlsInput

    try:
        result = await use_case.execute(
            PreviewUrlsInput(
                car_trim_id=body.car_trim_id,
                pricing_platform_slug=body.pricing_platform_slug,
                city=body.city,
                production_year_min=body.production_year_min,
                production_year_max=body.production_year_max,
                usage_min=body.usage_min,
                usage_max=body.usage_max,
                sample_production_year=body.sample_production_year,
                sample_kilometer=body.sample_kilometer,
                color=body.color,
            )
        )
        return PreviewUrlsResponse(
            divar_url=result.divar_url,
            pricing_url=result.pricing_url,
            pricing_platform_slug=result.pricing_platform_slug,
            khodro45_url=result.khodro45_url,
            divar_path=result.divar_path,
            khodro45_slug=result.khodro45_slug,
            trim_name=result.trim_name,
            year_title=result.year_title,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/users/{user_id}/purchase-flow", response_model=PurchaseFlowResponse, status_code=201)
async def create_purchase_flow(
    user_id: UUID,
    body: PurchaseFlowCreate,
    use_case=Depends(get_create_purchase_flow_use_case),
):
    from src.application.use_cases.create_purchase_flow import CreatePurchaseFlowInput

    try:
        result = await use_case.execute(
            CreatePurchaseFlowInput(
                user_id=user_id,
                car_trim_id=body.car_trim_id,
                pricing_platform_slug=body.pricing_platform_slug,
                listing_platform_slugs=body.listing_platform_slugs,
                city=body.city,
                color=body.color,
                production_year_min=body.production_year_min,
                production_year_max=body.production_year_max,
                usage_min=body.usage_min,
                usage_max=body.usage_max,
                near_threshold_pct=body.near_threshold_pct,
                is_active=body.is_active,
            )
        )
        return PurchaseFlowResponse(
            purchase_request_id=result.purchase_request.id,
            crawl_target_id=result.crawl_targets[0].id if result.crawl_targets else None,
            crawl_target_ids=[t.id for t in result.crawl_targets],
            divar_url=result.divar_url,
            pricing_preview_url=result.pricing_preview_url,
            pricing_platform_slug=result.pricing_platform_slug,
            expires_at=result.expires_at,
            car_trim_id=result.purchase_request.car_trim_id,
            car_model_id=result.purchase_request.car_model_id,
            production_year_min=result.purchase_request.production_year_min,
            usage_max=result.purchase_request.usage_max,
            hamrah_preview_url=result.pricing_preview_url,
            listing_mapping_configured=result.listing_mapping_configured,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

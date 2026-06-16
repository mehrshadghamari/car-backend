from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from src.application.use_cases.create_purchase_flow import CreatePurchaseFlowInput
from src.application.use_cases.manage_purchase_requests import (
    ManagePurchaseRequestsUseCase,
    UpdatePurchaseRequestInput,
)
from src.domain.exceptions import EntityNotFoundError, ValidationError
from src.presentation.api.schemas import (
    PurchaseFlowResponse,
    PurchaseRequestCreate,
    PurchaseRequestResponse,
    PurchaseRequestUpdate,
)
from src.presentation.dependencies import (
    get_cancel_purchase_request_use_case,
    get_create_purchase_flow_use_case,
    get_purchase_requests_use_case,
)

router = APIRouter(tags=["purchase-requests"])


def _to_response(request) -> PurchaseRequestResponse:
    return PurchaseRequestResponse(
        id=request.id,
        user_id=request.user_id,
        car_trim_id=request.car_trim_id,
        car_model_id=request.car_model_id,
        crawl_target_id=request.crawl_target_id,
        pricing_platform_id=request.pricing_platform_id,
        city=request.city,
        color=request.color,
        production_year_min=request.production_year_min,
        production_year_max=request.production_year_max,
        usage_min=request.usage_min,
        usage_max=request.usage_max,
        generated_divar_url=request.generated_divar_url,
        is_active=request.is_active,
        near_threshold_pct=request.near_threshold_pct,
        poll_interval_sec=request.poll_interval_sec,
        max_listings_per_check=request.max_listings_per_check,
        expires_at=request.expires_at,
        created_at=request.created_at,
    )


@router.post("/users/{user_id}/purchase-requests", response_model=PurchaseFlowResponse, status_code=201)
async def create_purchase_request(
    user_id: UUID,
    body: PurchaseRequestCreate,
    use_case=Depends(get_create_purchase_flow_use_case),
):
    try:
        result = await use_case.execute(
            CreatePurchaseFlowInput(
                user_id=user_id,
                car_trim_id=body.car_trim_id,
                pricing_platform_slug=body.pricing_platform_slug,
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
            hamrah_preview_url=result.pricing_preview_url,
            car_trim_id=result.purchase_request.car_trim_id,
            car_model_id=result.purchase_request.car_model_id,
            production_year_min=result.purchase_request.production_year_min,
            usage_max=result.purchase_request.usage_max,
            listing_mapping_configured=result.listing_mapping_configured,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/users/{user_id}/purchase-requests", response_model=list[PurchaseRequestResponse])
async def list_purchase_requests(
    user_id: UUID,
    use_case: ManagePurchaseRequestsUseCase = Depends(get_purchase_requests_use_case),
):
    requests = await use_case.list_by_user(user_id)
    return [_to_response(r) for r in requests]


@router.patch("/purchase-requests/{request_id}", response_model=PurchaseRequestResponse)
async def update_purchase_request(
    request_id: UUID,
    body: PurchaseRequestUpdate,
    use_case: ManagePurchaseRequestsUseCase = Depends(get_purchase_requests_use_case),
    cancel_use_case=Depends(get_cancel_purchase_request_use_case),
):
    try:
        if body.is_active is False:
            request = await cancel_use_case.execute(request_id)
            if body.near_threshold_pct is not None:
                request = await use_case.update(
                    request_id,
                    UpdatePurchaseRequestInput(near_threshold_pct=body.near_threshold_pct),
                )
            return _to_response(request)
        request = await use_case.update(
            request_id,
            UpdatePurchaseRequestInput(
                is_active=body.is_active,
                near_threshold_pct=body.near_threshold_pct,
            ),
        )
        return _to_response(request)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

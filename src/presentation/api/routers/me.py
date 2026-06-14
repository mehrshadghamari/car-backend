from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from src.application.use_cases.create_purchase_flow import CreatePurchaseFlowInput
from src.domain.entities.user import User
from src.domain.exceptions import EntityNotFoundError, ValidationError
from src.infrastructure.persistence.crawl_results_repository import SqlAlchemyCrawlResultsRepository
from src.infrastructure.tasks.crawl_tasks import schedule_crawl
from src.presentation.api.deps_auth import get_current_user
from src.presentation.api.schemas import (
    MyPurchaseDetailResponse,
    MyPurchaseSummary,
    PurchaseFlowResponse,
    UserPurchaseCreate,
)
from src.presentation.dependencies import (
    get_create_purchase_flow_use_case,
    get_crawl_results_repo,
)

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/purchase-requests", response_model=list[MyPurchaseSummary])
async def list_my_purchases(
    user: User = Depends(get_current_user),
    repo: SqlAlchemyCrawlResultsRepository = Depends(get_crawl_results_repo),
):
    rows = await repo.list_for_user(user.id)
    return [MyPurchaseSummary(**row) for row in rows]


@router.get("/purchase-requests/{purchase_request_id}", response_model=MyPurchaseDetailResponse)
async def get_my_purchase_detail(
    purchase_request_id: UUID,
    user: User = Depends(get_current_user),
    repo: SqlAlchemyCrawlResultsRepository = Depends(get_crawl_results_repo),
):
    detail = await repo.get_detail_for_user(purchase_request_id, user.id)
    if not detail:
        raise HTTPException(status_code=404, detail="درخواست خرید پیدا نشد")
    return MyPurchaseDetailResponse(**detail)


@router.post("/purchase-requests", response_model=PurchaseFlowResponse, status_code=201)
async def create_my_purchase(
    body: UserPurchaseCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    use_case=Depends(get_create_purchase_flow_use_case),
):
    try:
        result = await use_case.execute(
            CreatePurchaseFlowInput(
                user_id=user.id,
                car_trim_id=body.car_trim_id,
                pricing_platform_slug=body.pricing_platform_slug,
                city=body.city,
                color=body.color,
                production_year_min=body.production_year_min,
                production_year_max=body.production_year_max,
                usage_min=body.usage_min,
                usage_max=body.usage_max,
            )
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if body.run_crawl and result.crawl_targets:
        for target in result.crawl_targets:
            schedule_crawl(str(target.id), background_tasks, force=True)

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

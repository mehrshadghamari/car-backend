from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from src.application.use_cases.create_purchase_flow import CreatePurchaseFlowInput
from src.application.use_cases.manage_users import CreateUserInput
from src.domain.exceptions import EntityNotFoundError, ValidationError
from src.infrastructure.tasks.crawl_tasks import run_crawl_and_notify
from src.presentation.api.schemas import ScenarioRunRequest, ScenarioRunResponse
from src.presentation.dependencies import (
    get_create_purchase_flow_use_case,
    get_users_use_case,
)

router = APIRouter(prefix="/flow", tags=["flow"])


@router.post("/scenario", response_model=ScenarioRunResponse, status_code=201)
async def run_scenario(
    body: ScenarioRunRequest,
    background_tasks: BackgroundTasks,
    use_case=Depends(get_create_purchase_flow_use_case),
    users_uc=Depends(get_users_use_case),
):
    """
    End-to-end test scenario:
    1. Create user (or use existing)
    2. Create purchase flow (car model + filters -> Divar URL + crawl target)
    3. Optionally trigger crawl immediately
    """
    if body.user_id:
        user = await users_uc.get(body.user_id)
        user_id = user.id
    else:
        import time

        phone = body.phone
        existing = await users_uc.get_by_phone(phone)
        if existing:
            phone = f"09{int(time.time()) % 1000000000:09d}"[-11:]
        user = await users_uc.create(
            CreateUserInput(
                phone=phone,
                source_channel=body.source_channel,
                first_name=body.first_name,
                last_name=body.last_name,
            )
        )
        user_id = user.id

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
            )
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    crawl_result = None
    if body.run_crawl and result.crawl_targets:
        for target in result.crawl_targets:
            background_tasks.add_task(run_crawl_and_notify, str(target.id))
        crawl_result = "crawl_started"

    return ScenarioRunResponse(
        user_id=user_id,
        purchase_request_id=result.purchase_request.id,
        crawl_target_id=result.crawl_targets[0].id if result.crawl_targets else None,
        crawl_target_ids=[t.id for t in result.crawl_targets],
        divar_url=result.divar_url,
        pricing_preview_url=result.pricing_preview_url,
        pricing_platform_slug=result.pricing_platform_slug,
        expires_at=result.expires_at,
        hamrah_preview_url=result.pricing_preview_url,
        crawl_status=crawl_result,
    )

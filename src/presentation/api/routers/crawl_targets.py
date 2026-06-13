from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from src.application.use_cases.manage_crawl_targets import (
    CreateCrawlTargetInput,
    ManageCrawlTargetsUseCase,
    UpdateCrawlTargetInput,
)
from src.domain.exceptions import EntityNotFoundError, ValidationError
from src.infrastructure.tasks.crawl_tasks import run_crawl_and_notify
from src.presentation.api.schemas import (
    CrawlRunResponse,
    CrawlTargetCreate,
    CrawlTargetResponse,
    CrawlTargetUpdate,
)
from src.presentation.dependencies import get_crawl_run_repo, get_crawl_targets_use_case

router = APIRouter(prefix="/crawl-targets", tags=["crawl-targets"])


@router.post("", response_model=CrawlTargetResponse, status_code=201)
async def create_crawl_target(
    body: CrawlTargetCreate,
    use_case: ManageCrawlTargetsUseCase = Depends(get_crawl_targets_use_case),
):
    try:
        target = await use_case.create(
            CreateCrawlTargetInput(
                listing_url=body.listing_url,
                vehicle_context=body.vehicle_context.model_dump(),
                source=body.source,
                poll_interval_sec=body.poll_interval_sec,
                is_active=body.is_active,
            )
        )
        return CrawlTargetResponse(
            id=target.id,
            source=target.source,
            listing_url=target.listing_url,
            vehicle_context=target.vehicle_context.to_dict(),
            is_active=target.is_active,
            poll_interval_sec=target.poll_interval_sec,
            created_at=target.created_at,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=list[CrawlTargetResponse])
async def list_crawl_targets(
    active_only: bool = False,
    use_case: ManageCrawlTargetsUseCase = Depends(get_crawl_targets_use_case),
):
    targets = await use_case.list(active_only=active_only)
    return [
        CrawlTargetResponse(
            id=t.id,
            source=t.source,
            listing_url=t.listing_url,
            vehicle_context=t.vehicle_context.to_dict(),
            is_active=t.is_active,
            poll_interval_sec=t.poll_interval_sec,
            created_at=t.created_at,
        )
        for t in targets
    ]


@router.get("/{target_id}", response_model=CrawlTargetResponse)
async def get_crawl_target(
    target_id: UUID,
    use_case: ManageCrawlTargetsUseCase = Depends(get_crawl_targets_use_case),
):
    try:
        target = await use_case.get(target_id)
        return CrawlTargetResponse(
            id=target.id,
            source=target.source,
            listing_url=target.listing_url,
            vehicle_context=target.vehicle_context.to_dict(),
            is_active=target.is_active,
            poll_interval_sec=target.poll_interval_sec,
            created_at=target.created_at,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{target_id}", response_model=CrawlTargetResponse)
async def update_crawl_target(
    target_id: UUID,
    body: CrawlTargetUpdate,
    use_case: ManageCrawlTargetsUseCase = Depends(get_crawl_targets_use_case),
):
    try:
        target = await use_case.update(
            target_id,
            UpdateCrawlTargetInput(
                listing_url=body.listing_url,
                vehicle_context=body.vehicle_context.model_dump() if body.vehicle_context else None,
                poll_interval_sec=body.poll_interval_sec,
                is_active=body.is_active,
            ),
        )
        return CrawlTargetResponse(
            id=target.id,
            source=target.source,
            listing_url=target.listing_url,
            vehicle_context=target.vehicle_context.to_dict(),
            is_active=target.is_active,
            poll_interval_sec=target.poll_interval_sec,
            created_at=target.created_at,
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{target_id}", status_code=204)
async def delete_crawl_target(
    target_id: UUID,
    use_case: ManageCrawlTargetsUseCase = Depends(get_crawl_targets_use_case),
):
    try:
        await use_case.delete(target_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{target_id}/crawl-now", status_code=202)
async def crawl_now(
    target_id: UUID,
    background_tasks: BackgroundTasks,
):
    background_tasks.add_task(run_crawl_and_notify, str(target_id))
    return {"status": "accepted", "crawl_target_id": str(target_id)}


@router.get("/{target_id}/runs", response_model=list[CrawlRunResponse])
async def list_crawl_runs(
    target_id: UUID,
    limit: int = 20,
    crawl_run_repo=Depends(get_crawl_run_repo),
):
    runs = await crawl_run_repo.list_by_target(target_id, limit=limit)
    return [
        CrawlRunResponse(
            id=r.id,
            crawl_target_id=r.crawl_target_id,
            status=r.status.value,
            started_at=r.started_at,
            finished_at=r.finished_at,
            posts_found=r.posts_found,
            opportunities_found=r.opportunities_found,
            error_message=r.error_message,
        )
        for r in runs
    ]

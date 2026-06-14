from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from src.infrastructure.tasks.crawl_tasks import schedule_crawl
from src.domain.exceptions import EntityNotFoundError, ValidationError
from src.presentation.api.schemas import CrawlTaskStatusResponse
from src.presentation.dependencies import get_crawl_run_repo, get_db_session, get_run_purchase_crawl_use_case
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/crawl-tasks", tags=["crawl-tasks"])


@router.get("/status", response_model=CrawlTaskStatusResponse)
async def crawl_task_status(
    session: AsyncSession = Depends(get_db_session),
    crawl_run_repo=Depends(get_crawl_run_repo),
):
    from sqlalchemy import func, select

    from src.infrastructure.config import get_settings
    from src.infrastructure.persistence.models import PurchaseRequestModel

    settings = get_settings()
    stale_recovered = await crawl_run_repo.recover_stale_runs()

    active_purchases = (
        await session.execute(
            select(func.count())
            .select_from(PurchaseRequestModel)
            .where(PurchaseRequestModel.is_active.is_(True))
        )
    ).scalar() or 0

    running = await crawl_run_repo.count_by_status("running")
    failed = await crawl_run_repo.count_by_status("failed")
    completed = await crawl_run_repo.count_by_status("completed")

    redis_ok = False
    redis_error = None
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(settings.redis_url, decode_responses=True)
        redis_ok = await client.ping()
        await client.aclose()
    except Exception as exc:
        redis_error = str(exc)

    hints: list[str] = []
    if running:
        hints.append(f"{running} crawl(s) currently running")
    if not redis_ok:
        hints.append("Redis unreachable — Celery scheduler will not work")
    if redis_ok:
        hints.append(
            f"Pool refresh every {settings.crawl_pool_refresh_minutes} min when a car model has "
            f"open purchase requests (active for {settings.purchase_active_days} days). "
            "Run: celery -A src.infrastructure.tasks.celery_app worker "
            "and celery -A src.infrastructure.tasks.celery_app beat"
        )
    if stale_recovered:
        hints.append(
            f"Recovered {stale_recovered} interrupted crawl(s) — use 'Run crawl now' to retry"
        )
    if failed and not completed:
        hints.append("Recent crawls failed — open purchase detail to see diagnostics")

    return CrawlTaskStatusResponse(
        redis_ok=redis_ok,
        redis_error=redis_error,
        celery_broker=settings.celery_broker_url,
        scheduler_note=(
            f"Celery Beat refetches Divar pools every {settings.crawl_pool_refresh_minutes} minutes "
            f"only for car models with open purchase requests (max {settings.purchase_active_days} days)"
        ),
        active_purchases=active_purchases,
        running_crawls=running,
        completed_crawls=completed,
        failed_crawls=failed,
        stale_runs_recovered=stale_recovered,
        hints=hints,
    )


@router.post("/purchase/{purchase_request_id}/run-now", status_code=202)
async def run_crawl_for_purchase(
    purchase_request_id: UUID,
    background_tasks: BackgroundTasks,
    use_case=Depends(get_run_purchase_crawl_use_case),
):
    try:
        target_ids = [str(tid) for tid in await use_case.prepare(purchase_request_id)]
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not target_ids:
        raise HTTPException(
            status_code=400,
            detail=(
                "برای این تریم نگاشت Divar تنظیم نشده — "
                "ابتدا در Trim Mapping پیکربندی کنید"
            ),
        )

    modes: list[str] = []
    for target_id in target_ids:
        modes.append(schedule_crawl(target_id, background_tasks, force=True))

    return {
        "status": "accepted",
        "purchase_request_id": str(purchase_request_id),
        "crawl_target_ids": target_ids,
        "schedule_modes": modes,
        "message": "Crawl started in background — refresh detail in ~30s to see diagnostics",
    }

import asyncio
import logging
from uuid import UUID

import redis.asyncio as aioredis

from src.application.services.crawl_scheduler import (
    collect_pool_ids_for_active_purchases,
    pool_needs_crawl,
    pool_recently_crawled,
)
from src.application.use_cases.crawl_and_evaluate import CrawlAndEvaluateUseCase
from src.application.use_cases.crawl_retention import CrawlRetentionUseCase
from src.domain.compat import utc_now
from src.domain.services.crawl_schedule_window import is_crawl_allowed_in_tehran
from src.infrastructure.adapters.divar.divar_adapter import DivarListingAdapter
from src.infrastructure.adapters.pricing_factory import PricingServiceFactory
from src.infrastructure.config import get_settings
from src.infrastructure.persistence.task_database import task_db_session
from src.infrastructure.persistence.car_catalog_repositories import SqlAlchemyCarTrimRepository
from src.infrastructure.persistence.platform_repositories import SqlAlchemyPlatformRepository
from src.infrastructure.persistence.repositories import (
    SqlAlchemyCrawlRunRepository,
    SqlAlchemyCrawlTargetRepository,
    SqlAlchemyListingRepository,
    SqlAlchemyMarketPriceRepository,
    SqlAlchemyOpportunityRepository,
    SqlAlchemyPurchaseRequestRepository,
)
from src.infrastructure.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)
settings = get_settings()


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _crawl_and_notify_async(crawl_target_id: str, *, force: bool = False) -> dict:
    redis_client = aioredis.from_url(settings.redis_url, decode_responses=False)
    divar = DivarListingAdapter(settings)
    pricing_factory = PricingServiceFactory(settings, redis_client)

    try:
        async with task_db_session() as session:
            crawl_use_case = CrawlAndEvaluateUseCase(
                crawl_target_repo=SqlAlchemyCrawlTargetRepository(session),
                listing_repo=SqlAlchemyListingRepository(session),
                market_price_repo=SqlAlchemyMarketPriceRepository(session),
                opportunity_repo=SqlAlchemyOpportunityRepository(session),
                crawl_run_repo=SqlAlchemyCrawlRunRepository(session),
                purchase_request_repo=SqlAlchemyPurchaseRequestRepository(session),
                platform_repo=SqlAlchemyPlatformRepository(session),
                car_trim_repo=SqlAlchemyCarTrimRepository(session),
                divar_port=divar,
                pricing_factory=pricing_factory,
                settings=settings,
                max_concurrent_details=settings.divar_max_concurrent_details,
            )
            crawl_run = await crawl_use_case.execute(crawl_target_id, force=force)
            new_opp_ids = getattr(crawl_run, "new_opportunity_ids", [])

            return {
                "crawl_run_id": str(crawl_run.id),
                "status": crawl_run.status.value,
                "posts_found": crawl_run.posts_found,
                "opportunities_found": crawl_run.opportunities_found,
                "new_opportunity_ids": new_opp_ids,
                "sms_sent": 0,
            }
    finally:
        await divar.close()
        await pricing_factory.close()
        await redis_client.aclose()


@celery_app.task(name="src.infrastructure.tasks.crawl_tasks.crawl_target_job")
def crawl_target_job(crawl_target_id: str, force: bool = False) -> dict:
    logger.info("Starting crawl for target %s (force=%s)", crawl_target_id, force)
    return _run_async(_crawl_and_notify_async(crawl_target_id, force=force))


def run_crawl_and_notify(crawl_target_id: str, *, force: bool = False) -> dict:
    """Synchronous helper for FastAPI background tasks."""
    return _run_async(_crawl_and_notify_async(crawl_target_id, force=force))


def _safe_run_crawl(crawl_target_id: str) -> None:
    try:
        result = run_crawl_and_notify(crawl_target_id, force=True)
        logger.info(
            "Manual crawl finished for %s — status=%s posts=%s",
            crawl_target_id,
            result.get("status"),
            result.get("posts_found"),
        )
    except Exception:
        logger.exception("Manual crawl failed for %s", crawl_target_id)


def schedule_crawl(
    crawl_target_id: str,
    background_tasks=None,
    *,
    force: bool = False,
) -> str:
    """Queue crawl via Celery when available, else run in-process after response."""
    target_id = str(crawl_target_id)
    if force:
        if background_tasks is not None:
            background_tasks.add_task(_safe_run_crawl, target_id)
            return "background_forced"
        run_crawl_and_notify(target_id, force=True)
        return "sync_forced"
    try:
        crawl_target_job.delay(target_id, force=False)
        return "celery"
    except Exception:
        logger.warning(
            "Celery unavailable — running crawl in-process for target %s",
            target_id,
            exc_info=True,
        )
    if background_tasks is not None:
        background_tasks.add_task(run_crawl_and_notify, target_id)
        return "background"
    run_crawl_and_notify(target_id)
    return "sync"


@celery_app.task(name="src.infrastructure.tasks.crawl_tasks.schedule_active_crawls")
def schedule_active_crawls() -> dict:
    """
    Refetch shared pools every CRAWL_POOL_REFRESH_MINUTES when a car model has
    at least one open purchase request. Skip models with no active purchases.
    """

    async def _schedule():
        if not is_crawl_allowed_in_tehran():
            logger.info("Outside Tehran crawl hours (08:00–22:00) — skipping schedule")
            return {"scheduled": 0, "skipped_quiet_hours": 1, "skipped_recent": 0}

        async with task_db_session() as session:
            target_repo = SqlAlchemyCrawlTargetRepository(session)
            purchase_repo = SqlAlchemyPurchaseRequestRepository(session)
            crawl_run_repo = SqlAlchemyCrawlRunRepository(session)

            active_purchases = await purchase_repo.list_active_non_expired()
            if not active_purchases:
                logger.info("No open purchase requests — skipping all Divar pool crawls")
                return {"scheduled": 0, "skipped_no_active_purchases": 0, "skipped_recent": 0}

            active_trim_ids = {p.car_trim_id for p in active_purchases if p.car_trim_id}
            platform_repo = SqlAlchemyPlatformRepository(session)
            active_mapping_ids = await platform_repo.list_active_listing_mapping_ids_for_trims(
                active_trim_ids
            )
            pool_ids = collect_pool_ids_for_active_purchases(active_purchases)
            now = utc_now()

            scheduled = 0
            skipped_no_active = 0
            skipped_recent = 0

            for pool_id in pool_ids:
                pool = await target_repo.get_by_id(pool_id)
                if (
                    pool
                    and pool.is_shared_pool
                    and not pool.is_active
                    and pool.listing_mapping_id
                ):
                    canonical = await target_repo.get_shared_pool(
                        pool.listing_mapping_id,
                        pool.city or "tehran",
                        pool.source,
                        pool_production_year=pool.pool_production_year,
                    )
                    if canonical:
                        pool_id = canonical.id
                        pool = canonical

                if not pool or not pool_needs_crawl(pool, active_listing_mapping_ids=active_mapping_ids):
                    skipped_no_active += 1
                    continue

                last_run = await crawl_run_repo.get_latest_for_target(pool_id)
                refresh_sec = pool.poll_interval_sec or settings.crawl_pool_refresh_sec
                if pool_recently_crawled(last_run, refresh_sec=refresh_sec, now=now):
                    skipped_recent += 1
                    continue

                crawl_target_job.delay(str(pool_id))
                scheduled += 1

            logger.info(
                "Crawl schedule: %s queued, %s skipped (no active car model), %s skipped (recent)",
                scheduled,
                skipped_no_active,
                skipped_recent,
            )
            return {
                "scheduled": scheduled,
                "skipped_no_active_purchases": skipped_no_active,
                "skipped_recent": skipped_recent,
                "active_trims": len(active_trim_ids),
            }

    return _run_async(_schedule())


async def _purge_stale_crawl_data_async() -> dict:
    async with task_db_session() as session:
        use_case = CrawlRetentionUseCase(
            listing_repo=SqlAlchemyListingRepository(session),
            purchase_request_repo=SqlAlchemyPurchaseRequestRepository(session),
            settings=settings,
        )
        return await use_case.execute()


@celery_app.task(name="src.infrastructure.tasks.crawl_tasks.purge_stale_crawl_data")
def purge_stale_crawl_data() -> dict:
    """Deactivate listings/purchases older than retention window and bulk-delete inactive pool data."""
    logger.info("Running crawl retention purge")
    return _run_async(_purge_stale_crawl_data_async())


@celery_app.task(name="src.infrastructure.tasks.crawl_tasks.refresh_hamrah_build_id")
def refresh_hamrah_build_id() -> str:
    async def _refresh():
        redis_client = aioredis.from_url(settings.redis_url, decode_responses=False)
        from src.infrastructure.adapters.hamrah_mechanic.hamrah_adapter import HamrahMechanicPricingAdapter

        hamrah = HamrahMechanicPricingAdapter(settings, redis_client)
        try:
            return await hamrah.refresh_build_id()
        finally:
            await hamrah.close()
            await redis_client.aclose()

    return _run_async(_refresh())

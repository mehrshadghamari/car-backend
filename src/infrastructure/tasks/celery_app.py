from datetime import timedelta

from celery import Celery
from celery.schedules import crontab

from src.infrastructure.config import get_settings

settings = get_settings()

celery_app = Celery(
    "car_backend",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["src.infrastructure.tasks.crawl_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Tehran",
    enable_utc=True,
    beat_schedule={
        "refresh-hamrah-build-id": {
            "task": "src.infrastructure.tasks.crawl_tasks.refresh_hamrah_build_id",
            "schedule": crontab(hour=3, minute=0),
        },
        "schedule-active-crawls": {
            "task": "src.infrastructure.tasks.crawl_tasks.schedule_active_crawls",
            "schedule": timedelta(minutes=settings.crawl_pool_refresh_minutes),
        },
        "purge-stale-crawl-data": {
            "task": "src.infrastructure.tasks.crawl_tasks.purge_stale_crawl_data",
            "schedule": crontab(hour=4, minute=0),
        },
    },
)

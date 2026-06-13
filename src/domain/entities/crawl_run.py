from dataclasses import dataclass
from datetime import datetime
from src.domain.compat import StrEnum
from uuid import UUID


class CrawlRunStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CrawlRun:
    id: UUID
    crawl_target_id: UUID
    status: CrawlRunStatus
    started_at: datetime
    posts_found: int = 0
    opportunities_found: int = 0
    finished_at: datetime | None = None
    error_message: str | None = None
    diagnostics: list[dict] | None = None

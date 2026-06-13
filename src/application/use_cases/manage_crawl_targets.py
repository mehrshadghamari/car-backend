from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from src.application.ports.repositories import CrawlTargetRepository
from src.domain.entities.crawl_target import CrawlTarget, VehicleContext
from src.domain.exceptions import EntityNotFoundError, ValidationError


@dataclass
class CreateCrawlTargetInput:
    listing_url: str
    vehicle_context: dict[str, Any]
    source: str = "divar"
    poll_interval_sec: int = 300
    is_active: bool = True


@dataclass
class UpdateCrawlTargetInput:
    listing_url: str | None = None
    vehicle_context: dict[str, Any] | None = None
    poll_interval_sec: int | None = None
    is_active: bool | None = None


class ManageCrawlTargetsUseCase:
    def __init__(self, crawl_target_repo: CrawlTargetRepository):
        self._repo = crawl_target_repo

    async def create(self, input_dto: CreateCrawlTargetInput) -> CrawlTarget:
        if not input_dto.listing_url:
            raise ValidationError("listing_url is required")
        target = CrawlTarget(
            id=uuid4(),
            source=input_dto.source,
            listing_url=input_dto.listing_url,
            vehicle_context=VehicleContext.from_dict(input_dto.vehicle_context),
            is_active=input_dto.is_active,
            poll_interval_sec=input_dto.poll_interval_sec,
        )
        return await self._repo.save(target)

    async def get(self, target_id: UUID) -> CrawlTarget:
        target = await self._repo.get_by_id(target_id)
        if not target:
            raise EntityNotFoundError(f"Crawl target {target_id} not found")
        return target

    async def list(self, active_only: bool = False) -> list[CrawlTarget]:
        return await self._repo.list_all(active_only=active_only)

    async def update(self, target_id: UUID, input_dto: UpdateCrawlTargetInput) -> CrawlTarget:
        target = await self.get(target_id)
        if input_dto.listing_url is not None:
            target.listing_url = input_dto.listing_url
        if input_dto.vehicle_context is not None:
            target.vehicle_context = VehicleContext.from_dict(input_dto.vehicle_context)
        if input_dto.poll_interval_sec is not None:
            target.poll_interval_sec = input_dto.poll_interval_sec
        if input_dto.is_active is not None:
            target.is_active = input_dto.is_active
        return await self._repo.save(target)

    async def delete(self, target_id: UUID) -> None:
        if not await self._repo.delete(target_id):
            raise EntityNotFoundError(f"Crawl target {target_id} not found")

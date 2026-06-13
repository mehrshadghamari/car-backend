from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID, uuid4

from src.application.ports.repositories import PurchaseRequestRepository
from src.domain.entities.purchase_request import PurchaseRequest
from src.domain.exceptions import EntityNotFoundError


@dataclass
class CreatePurchaseRequestInput:
    user_id: UUID
    crawl_target_id: UUID
    near_threshold_pct: Decimal | None = None
    is_active: bool = True


@dataclass
class UpdatePurchaseRequestInput:
    is_active: bool | None = None
    near_threshold_pct: Decimal | None = None


class ManagePurchaseRequestsUseCase:
    def __init__(self, purchase_request_repo: PurchaseRequestRepository):
        self._repo = purchase_request_repo

    async def create(self, input_dto: CreatePurchaseRequestInput) -> PurchaseRequest:
        request = PurchaseRequest(
            id=uuid4(),
            user_id=input_dto.user_id,
            crawl_target_id=input_dto.crawl_target_id,
            is_active=input_dto.is_active,
            near_threshold_pct=input_dto.near_threshold_pct,
        )
        return await self._repo.save(request)

    async def get(self, request_id: UUID) -> PurchaseRequest:
        request = await self._repo.get_by_id(request_id)
        if not request:
            raise EntityNotFoundError(f"Purchase request {request_id} not found")
        return request

    async def list_by_user(self, user_id: UUID) -> list[PurchaseRequest]:
        return await self._repo.list_by_user(user_id)

    async def update(self, request_id: UUID, input_dto: UpdatePurchaseRequestInput) -> PurchaseRequest:
        request = await self.get(request_id)
        if input_dto.is_active is not None:
            request.is_active = input_dto.is_active
        if input_dto.near_threshold_pct is not None:
            request.near_threshold_pct = input_dto.near_threshold_pct
        return await self._repo.save(request)

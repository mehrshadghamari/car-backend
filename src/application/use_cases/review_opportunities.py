"""Staff approve/reject opportunities before they appear in the client app."""

from dataclasses import dataclass
from uuid import UUID

from src.application.ports.repositories import OpportunityRepository, PurchaseRequestRepository
from src.domain.entities.opportunity import OpportunityStatus
from src.domain.exceptions import EntityNotFoundError, ValidationError


@dataclass
class ReviewOpportunitiesInput:
    purchase_request_id: UUID
    opportunity_ids: list[UUID]
    action: str  # approve | reject


@dataclass
class ReviewOpportunitiesResult:
    updated: int
    action: str


class ReviewOpportunitiesUseCase:
    def __init__(
        self,
        opportunity_repo: OpportunityRepository,
        purchase_request_repo: PurchaseRequestRepository,
    ):
        self._opportunity_repo = opportunity_repo
        self._purchase_request_repo = purchase_request_repo

    async def execute(self, input_dto: ReviewOpportunitiesInput) -> ReviewOpportunitiesResult:
        if input_dto.action not in ("approve", "reject"):
            raise ValidationError("action must be approve or reject")
        if not input_dto.opportunity_ids:
            raise ValidationError("حداقل یک فرصت را انتخاب کنید")

        purchase = await self._purchase_request_repo.get_by_id(input_dto.purchase_request_id)
        if not purchase:
            raise EntityNotFoundError("درخواست خرید پیدا نشد")

        target_status = (
            OpportunityStatus.APPROVED
            if input_dto.action == "approve"
            else OpportunityStatus.REJECTED
        )
        updated = 0
        for opp_id in input_dto.opportunity_ids:
            opp = await self._opportunity_repo.get_by_id(opp_id)
            if not opp or opp.purchase_request_id != purchase.id:
                continue
            if opp.status == OpportunityStatus.EXPIRED:
                continue
            if input_dto.action == "approve":
                if opp.status != OpportunityStatus.NEW:
                    continue
            elif opp.status in (OpportunityStatus.REJECTED, OpportunityStatus.EXPIRED, OpportunityStatus.NOTIFIED):
                continue
            opp.status = target_status
            await self._opportunity_repo.save(opp)
            updated += 1

        if updated == 0:
            raise ValidationError("هیچ فرصت قابل بررسی پیدا نشد")

        return ReviewOpportunitiesResult(updated=updated, action=input_dto.action)

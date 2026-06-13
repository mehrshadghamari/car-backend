from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from src.application.use_cases.send_opportunity_sms import SendOpportunitySmsInput
from src.domain.exceptions import EntityNotFoundError, ValidationError
from src.infrastructure.persistence.crawl_results_repository import SqlAlchemyCrawlResultsRepository
from src.presentation.api.schemas import (
    CrawlResultDetailResponse,
    CrawlResultOverviewItem,
    SendOpportunitySmsRequest,
    SendOpportunitySmsResponse,
)
from src.presentation.dependencies import get_crawl_results_repo, get_send_opportunity_sms_use_case

router = APIRouter(prefix="/crawl-results", tags=["crawl-results"])


@router.get("", response_model=list[CrawlResultOverviewItem])
async def list_crawl_results(
    limit: int = 100,
    repo: SqlAlchemyCrawlResultsRepository = Depends(get_crawl_results_repo),
):
    rows = await repo.list_overview(limit=limit)
    return [CrawlResultOverviewItem(**row) for row in rows]


@router.get("/{purchase_request_id}", response_model=CrawlResultDetailResponse)
async def get_crawl_result_detail(
    purchase_request_id: UUID,
    repo: SqlAlchemyCrawlResultsRepository = Depends(get_crawl_results_repo),
):
    detail = await repo.get_detail(purchase_request_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Purchase request not found")
    return CrawlResultDetailResponse(**detail)


@router.post("/{purchase_request_id}/send-sms", response_model=SendOpportunitySmsResponse)
async def send_opportunity_sms(
    purchase_request_id: UUID,
    body: SendOpportunitySmsRequest,
    use_case=Depends(get_send_opportunity_sms_use_case),
):
    try:
        result = await use_case.execute(
            SendOpportunitySmsInput(
                purchase_request_id=purchase_request_id,
                opportunity_ids=body.opportunity_ids,
                mode=body.mode,
            )
        )
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SendOpportunitySmsResponse(
        sms_sent=result.sms_sent,
        deliveries_created=result.deliveries_created,
        share_token=result.share_token,
        share_url=result.share_url,
    )

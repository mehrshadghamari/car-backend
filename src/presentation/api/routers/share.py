from fastapi import APIRouter, Depends, HTTPException

from src.domain.compat import utc_now
from src.infrastructure.persistence.crawl_results_repository import SqlAlchemyCrawlResultsRepository
from src.presentation.api.schemas import ShareBatchDetailResponse
from src.presentation.dependencies import get_crawl_results_repo, get_share_batch_repo

router = APIRouter(prefix="/share", tags=["share"])


@router.get("/{token}", response_model=ShareBatchDetailResponse)
async def get_share_batch(
    token: str,
    share_repo=Depends(get_share_batch_repo),
    crawl_repo: SqlAlchemyCrawlResultsRepository = Depends(get_crawl_results_repo),
):
    batch = await share_repo.get_by_token(token)
    if not batch or batch.expires_at <= utc_now():
        raise HTTPException(status_code=404, detail="لینک منقضی یا نامعتبر است")
    detail = await crawl_repo.get_detail(batch.purchase_request_id)
    if not detail:
        raise HTTPException(status_code=404, detail="درخواست خرید پیدا نشد")
    selected = {str(i) for i in batch.opportunity_ids}
    opps = [o for o in detail["opportunities"] if o["id"] in selected]
    return ShareBatchDetailResponse(
        purchase_request=detail["purchase_request"],
        car_model=detail["car_model"],
        opportunities=opps,
    )

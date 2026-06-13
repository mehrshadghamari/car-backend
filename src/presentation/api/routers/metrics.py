from fastapi import APIRouter, Depends

from src.application.use_cases.metrics import MetricsUseCase
from src.presentation.api.schemas import MetricsSummaryResponse
from src.presentation.dependencies import get_metrics_use_case

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/summary", response_model=MetricsSummaryResponse)
async def get_metrics_summary(
    days: int = 30,
    use_case: MetricsUseCase = Depends(get_metrics_use_case),
):
    summary = await use_case.get_summary(days=days)
    return MetricsSummaryResponse(
        opportunities_detected=summary.opportunities_detected,
        opportunities_delivered=summary.opportunities_delivered,
        sms_click_count=summary.sms_click_count,
        click_rate_pct=summary.click_rate_pct,
        avg_time_to_click_sec=summary.avg_time_to_click_sec,
    )

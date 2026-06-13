from dataclasses import dataclass
from datetime import timedelta

from src.domain.compat import utc_now

from sqlalchemy import func, select

from src.application.ports.repositories import DeliveryRepository, OpportunityRepository
from src.infrastructure.persistence.database import async_session_factory
from src.infrastructure.persistence.models import OpportunityModel


@dataclass
class MetricsSummary:
    opportunities_detected: int
    opportunities_delivered: int
    sms_click_count: int
    click_rate_pct: float
    avg_time_to_click_sec: float | None


class MetricsUseCase:
    def __init__(
        self,
        opportunity_repo: OpportunityRepository,
        delivery_repo: DeliveryRepository,
    ):
        self._opportunity_repo = opportunity_repo
        self._delivery_repo = delivery_repo

    async def get_summary(self, days: int = 30) -> MetricsSummary:
        since = utc_now() - timedelta(days=days)
        opportunities = await self._opportunity_repo.list_all(limit=10000)
        recent_opps = [o for o in opportunities if o.created_at and o.created_at >= since]

        delivered = await self._delivery_repo.count_deliveries(since=since)
        clicks = await self._delivery_repo.count_clicks(since=since)

        click_rate = (clicks / delivered * 100) if delivered else 0.0

        avg_time = None
        async with async_session_factory() as session:
            from src.infrastructure.persistence.models import GatewayClickModel

            result = await session.execute(
                select(func.avg(GatewayClickModel.time_to_click_sec)).where(
                    GatewayClickModel.time_to_click_sec.isnot(None),
                    GatewayClickModel.clicked_at >= since,
                )
            )
            avg_val = result.scalar()
            if avg_val is not None:
                avg_time = float(avg_val)

        return MetricsSummary(
            opportunities_detected=len(recent_opps),
            opportunities_delivered=delivered,
            sms_click_count=clicks,
            click_rate_pct=round(click_rate, 2),
            avg_time_to_click_sec=avg_time,
        )

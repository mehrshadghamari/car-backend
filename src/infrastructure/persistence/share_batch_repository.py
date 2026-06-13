from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.persistence.models import OpportunityShareBatchModel


class SqlAlchemyShareBatchRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(
        self,
        *,
        token: str,
        purchase_request_id: UUID,
        user_id: UUID,
        opportunity_ids: list[str],
        expires_at: datetime,
    ) -> None:
        self._session.add(
            OpportunityShareBatchModel(
                id=uuid4(),
                token=token,
                purchase_request_id=purchase_request_id,
                user_id=user_id,
                opportunity_ids=opportunity_ids,
                expires_at=expires_at,
            )
        )
        await self._session.commit()

    async def get_by_token(self, token: str) -> OpportunityShareBatchModel | None:
        result = await self._session.execute(
            select(OpportunityShareBatchModel).where(OpportunityShareBatchModel.token == token)
        )
        return result.scalar_one_or_none()

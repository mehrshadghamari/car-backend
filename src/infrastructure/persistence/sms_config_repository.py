from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.application.ports.sms_config_repository import SmsConfigRepository
from src.domain.entities.sms_config import SmsProvider, SmsTemplate
from src.infrastructure.persistence.models import SmsProviderModel, SmsTemplateModel


def _provider_from_model(model: SmsProviderModel) -> SmsProvider:
    return SmsProvider(
        id=model.id,
        slug=model.slug,
        name=model.name,
        driver=model.driver,
        is_active=model.is_active,
        config=model.config or {},
    )


def _template_from_model(model: SmsTemplateModel) -> SmsTemplate:
    provider = _provider_from_model(model.provider) if model.provider else None
    return SmsTemplate(
        id=model.id,
        action=model.action,
        name=model.name,
        send_mode=model.send_mode,
        text_body=model.text_body,
        pattern_key=model.pattern_key,
        pattern_slots=list(model.pattern_slots or []),
        pattern_params=list(model.pattern_params or []),
        provider_id=model.provider_id,
        is_active=model.is_active,
        provider=provider,
    )


class SqlAlchemySmsConfigRepository(SmsConfigRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_active_template_by_action(self, action: str) -> SmsTemplate | None:
        stmt = (
            select(SmsTemplateModel)
            .options(joinedload(SmsTemplateModel.provider))
            .where(SmsTemplateModel.action == action, SmsTemplateModel.is_active.is_(True))
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _template_from_model(model) if model else None

    async def get_provider_by_id(self, provider_id: UUID) -> SmsProvider | None:
        model = await self._session.get(SmsProviderModel, provider_id)
        return _provider_from_model(model) if model else None

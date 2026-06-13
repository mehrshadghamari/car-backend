from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import attributes, joinedload

from src.domain.entities.platform import (
    DivarCarModel,
    DivarCity,
    ListingMapping,
    ListingPlatform,
    PricingPlatform,
    TrimPricingMapping,
)
from src.infrastructure.persistence.models import (
    CarTrimModel,
    DivarCarModelModel,
    DivarCityModel,
    ListingMappingModel,
    ListingMappingTrimModel,
    ListingPlatformModel,
    PricingPlatformModel,
    TrimPricingMappingModel,
)


def _listing_platform_to_domain(m: ListingPlatformModel) -> ListingPlatform:
    return ListingPlatform(
        id=m.id,
        slug=m.slug,
        name=m.name,
        fetch_strategy=m.fetch_strategy or "crawl",
        is_active=m.is_active,
        created_at=m.created_at,
    )


def _pricing_platform_to_domain(m: PricingPlatformModel) -> PricingPlatform:
    return PricingPlatform(
        id=m.id,
        slug=m.slug,
        name=m.name,
        fetch_strategy=m.fetch_strategy or "crawl",
        is_active=m.is_active,
        created_at=m.created_at,
    )


def _divar_city_to_domain(m: DivarCityModel) -> DivarCity:
    return DivarCity(id=m.id, slug=m.slug, display=m.display, is_active=m.is_active)


def _divar_car_model_to_domain(m: DivarCarModelModel) -> DivarCarModel:
    return DivarCarModel(id=m.id, slug=m.slug, display=m.display, is_active=m.is_active)


def _listing_mapping_to_domain(m: ListingMappingModel) -> ListingMapping:
    state = attributes.instance_state(m)
    if "trim_links" in state.unloaded:
        trim_ids: list[UUID] = []
    else:
        trim_ids = [link.trim_id for link in m.trim_links] if m.trim_links else []
    if "divar_car_model" in state.unloaded:
        divar_slug = ""
    else:
        divar_slug = m.divar_car_model.slug if m.divar_car_model else ""
    return ListingMapping(
        id=m.id,
        listing_platform_id=m.listing_platform_id,
        divar_car_model_id=m.divar_car_model_id,
        path=m.path,
        divar_brand_model=divar_slug,
        config=m.config,
        is_active=m.is_active,
        trim_ids=trim_ids,
    )


def _trim_pricing_mapping_to_domain(m: TrimPricingMappingModel) -> TrimPricingMapping:
    return TrimPricingMapping(
        id=m.id,
        trim_id=m.trim_id,
        pricing_platform_id=m.pricing_platform_id,
        slug=m.slug,
        config=m.config,
        is_active=m.is_active,
    )


class SqlAlchemyPlatformRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def list_listing_platforms(self, active_only: bool = True) -> list[ListingPlatform]:
        stmt = select(ListingPlatformModel)
        if active_only:
            stmt = stmt.where(ListingPlatformModel.is_active.is_(True))
        result = await self._session.execute(stmt)
        return [_listing_platform_to_domain(m) for m in result.scalars().all()]

    async def list_pricing_platforms(self, active_only: bool = True) -> list[PricingPlatform]:
        stmt = select(PricingPlatformModel)
        if active_only:
            stmt = stmt.where(PricingPlatformModel.is_active.is_(True))
        result = await self._session.execute(stmt)
        return [_pricing_platform_to_domain(m) for m in result.scalars().all()]

    async def get_pricing_platform_by_slug(self, slug: str) -> PricingPlatform | None:
        result = await self._session.execute(
            select(PricingPlatformModel).where(PricingPlatformModel.slug == slug)
        )
        model = result.scalar_one_or_none()
        return _pricing_platform_to_domain(model) if model else None

    async def get_listing_platform_by_slug(self, slug: str) -> ListingPlatform | None:
        result = await self._session.execute(
            select(ListingPlatformModel).where(ListingPlatformModel.slug == slug)
        )
        model = result.scalar_one_or_none()
        return _listing_platform_to_domain(model) if model else None

    async def get_pricing_platform_by_id(self, platform_id: UUID) -> PricingPlatform | None:
        model = await self._session.get(PricingPlatformModel, platform_id)
        return _pricing_platform_to_domain(model) if model else None

    async def get_listing_mappings_for_trim(
        self, trim_id: UUID, listing_platform_slug: str | None = None
    ) -> list[ListingMapping]:
        stmt = (
            select(ListingMappingModel)
            .join(ListingMappingTrimModel)
            .join(ListingPlatformModel)
            .options(
                joinedload(ListingMappingModel.trim_links),
                joinedload(ListingMappingModel.divar_car_model),
            )
            .where(
                ListingMappingTrimModel.trim_id == trim_id,
                ListingMappingModel.is_active.is_(True),
            )
        )
        if listing_platform_slug:
            stmt = stmt.where(ListingPlatformModel.slug == listing_platform_slug)
        result = await self._session.execute(stmt)
        return [_listing_mapping_to_domain(m) for m in result.scalars().unique().all()]

    async def get_listing_mapping_by_id(self, mapping_id: UUID) -> ListingMapping | None:
        stmt = (
            select(ListingMappingModel)
            .options(
                joinedload(ListingMappingModel.trim_links),
                joinedload(ListingMappingModel.divar_car_model),
            )
            .where(ListingMappingModel.id == mapping_id)
        )
        result = await self._session.execute(stmt)
        model = result.scalars().unique().one_or_none()
        return _listing_mapping_to_domain(model) if model else None

    async def get_pricing_mapping_for_trim(
        self, trim_id: UUID, pricing_platform_id: UUID
    ) -> TrimPricingMapping | None:
        stmt = (
            select(TrimPricingMappingModel)
            .where(
                TrimPricingMappingModel.trim_id == trim_id,
                TrimPricingMappingModel.pricing_platform_id == pricing_platform_id,
                TrimPricingMappingModel.is_active.is_(True),
            )
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _trim_pricing_mapping_to_domain(model) if model else None

    async def get_pricing_mapping(
        self, trim_id: UUID, pricing_platform_id: UUID
    ) -> TrimPricingMapping | None:
        return await self.get_pricing_mapping_for_trim(trim_id, pricing_platform_id)

    async def list_active_listing_mapping_ids_for_trims(self, trim_ids: set[UUID]) -> set[UUID]:
        if not trim_ids:
            return set()
        result = await self._session.execute(
            select(ListingMappingTrimModel.listing_mapping_id).where(
                ListingMappingTrimModel.trim_id.in_(trim_ids)
            )
        )
        return set(result.scalars().all())

    async def find_listing_mapping_for_model(
        self, model_id: UUID, listing_platform_slug: str
    ) -> ListingMapping | None:
        stmt = (
            select(ListingMappingModel)
            .join(ListingMappingTrimModel)
            .join(CarTrimModel, CarTrimModel.id == ListingMappingTrimModel.trim_id)
            .join(ListingPlatformModel)
            .options(
                joinedload(ListingMappingModel.trim_links),
                joinedload(ListingMappingModel.divar_car_model),
            )
            .where(
                CarTrimModel.model_id == model_id,
                ListingPlatformModel.slug == listing_platform_slug,
                ListingMappingModel.is_active.is_(True),
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalars().unique().one_or_none()
        return _listing_mapping_to_domain(model) if model else None

    async def link_trim_to_listing_mapping(self, trim_id: UUID, listing_mapping_id: UUID) -> None:
        existing = await self._session.execute(
            select(ListingMappingTrimModel).where(
                ListingMappingTrimModel.trim_id == trim_id,
                ListingMappingTrimModel.listing_mapping_id == listing_mapping_id,
            )
        )
        if existing.scalar_one_or_none():
            return
        self._session.add(
            ListingMappingTrimModel(
                id=uuid4(),
                listing_mapping_id=listing_mapping_id,
                trim_id=trim_id,
            )
        )
        await self._session.flush()

    async def create_listing_mapping(self, mapping: ListingMapping) -> ListingMapping:
        model = ListingMappingModel(
            id=mapping.id,
            listing_platform_id=mapping.listing_platform_id,
            divar_car_model_id=mapping.divar_car_model_id,
            path=mapping.path,
            config=mapping.config,
            is_active=mapping.is_active,
        )
        self._session.add(model)
        await self._session.flush()
        divar_model = await self.get_divar_car_model_by_id(mapping.divar_car_model_id)
        return ListingMapping(
            id=model.id,
            listing_platform_id=model.listing_platform_id,
            divar_car_model_id=model.divar_car_model_id,
            path=model.path,
            divar_brand_model=divar_model.slug if divar_model else mapping.divar_brand_model,
            config=model.config,
            is_active=model.is_active,
            trim_ids=[],
        )

    async def get_divar_car_model_by_id(self, model_id: UUID) -> DivarCarModel | None:
        model = await self._session.get(DivarCarModelModel, model_id)
        return _divar_car_model_to_domain(model) if model else None

    async def get_divar_car_model_by_slug(self, slug: str) -> DivarCarModel | None:
        result = await self._session.execute(
            select(DivarCarModelModel).where(DivarCarModelModel.slug == slug.strip())
        )
        model = result.scalar_one_or_none()
        return _divar_car_model_to_domain(model) if model else None

    async def list_divar_cities(
        self, *, q: str | None = None, limit: int = 500
    ) -> list[DivarCity]:
        stmt = select(DivarCityModel).where(DivarCityModel.is_active.is_(True))
        if q:
            like = f"%{q.strip()}%"
            stmt = stmt.where(
                DivarCityModel.slug.ilike(like) | DivarCityModel.display.ilike(like)
            )
        stmt = stmt.order_by(DivarCityModel.display).limit(limit)
        result = await self._session.execute(stmt)
        return [_divar_city_to_domain(m) for m in result.scalars().all()]

    async def list_divar_car_models(
        self, *, q: str | None = None, limit: int = 200
    ) -> list[DivarCarModel]:
        stmt = select(DivarCarModelModel).where(DivarCarModelModel.is_active.is_(True))
        if q:
            like = f"%{q.strip()}%"
            stmt = stmt.where(
                DivarCarModelModel.slug.ilike(like) | DivarCarModelModel.display.ilike(like)
            )
        stmt = stmt.order_by(DivarCarModelModel.display).limit(limit)
        result = await self._session.execute(stmt)
        return [_divar_car_model_to_domain(m) for m in result.scalars().all()]

    async def list_listing_mappings(self, model_id: UUID | None = None) -> list[dict]:
        stmt = (
            select(ListingMappingModel)
            .options(
                joinedload(ListingMappingModel.trim_links).joinedload(ListingMappingTrimModel.trim),
                joinedload(ListingMappingModel.listing_platform),
                joinedload(ListingMappingModel.divar_car_model),
            )
        )
        if model_id:
            stmt = stmt.join(ListingMappingTrimModel).join(CarTrimModel).where(
                CarTrimModel.model_id == model_id
            )
        result = await self._session.execute(stmt)
        rows: list[dict] = []
        for m in result.scalars().unique().all():
            rows.append(await self._listing_mapping_row(m))
        return rows

    async def listing_mapping_row(self, mapping_id: UUID) -> dict:
        stmt = (
            select(ListingMappingModel)
            .options(
                joinedload(ListingMappingModel.trim_links).joinedload(ListingMappingTrimModel.trim),
                joinedload(ListingMappingModel.listing_platform),
                joinedload(ListingMappingModel.divar_car_model),
            )
            .where(ListingMappingModel.id == mapping_id)
        )
        result = await self._session.execute(stmt)
        model = result.scalars().unique().one_or_none()
        if not model:
            raise ValueError("mapping not found")
        return await self._listing_mapping_row(model)

    async def _listing_mapping_row(self, m: ListingMappingModel) -> dict:
        trim_labels = []
        for link in m.trim_links or []:
            trim = link.trim
            if trim:
                trim_labels.append({"trim_id": str(trim.id), "name": trim.name})
        divar_model = m.divar_car_model
        return {
            "id": m.id,
            "listing_platform_slug": m.listing_platform.slug if m.listing_platform else None,
            "path": m.path,
            "divar_car_model_id": m.divar_car_model_id,
            "divar_car_model_slug": divar_model.slug if divar_model else "",
            "divar_car_model_display": divar_model.display if divar_model else "",
            "is_active": m.is_active,
            "trim_count": len(m.trim_links or []),
            "trims": trim_labels,
        }

    async def commit(self) -> None:
        await self._session.commit()

    async def save_listing_mapping(
        self, mapping: ListingMapping, *, trim_id: UUID
    ) -> ListingMapping:
        model = ListingMappingModel(
            id=mapping.id,
            listing_platform_id=mapping.listing_platform_id,
            divar_car_model_id=mapping.divar_car_model_id,
            path=mapping.path,
            config=mapping.config,
            is_active=mapping.is_active,
        )
        self._session.add(model)
        await self._session.flush()
        await self.link_trim_to_listing_mapping(trim_id, model.id)
        divar_model = await self.get_divar_car_model_by_id(mapping.divar_car_model_id)
        return ListingMapping(
            id=model.id,
            listing_platform_id=model.listing_platform_id,
            divar_car_model_id=model.divar_car_model_id,
            path=model.path,
            divar_brand_model=divar_model.slug if divar_model else mapping.divar_brand_model,
            config=model.config,
            is_active=model.is_active,
            trim_ids=[trim_id],
        )

    async def save_trim_pricing_mapping(self, mapping: TrimPricingMapping) -> TrimPricingMapping:
        model = TrimPricingMappingModel(
            id=mapping.id,
            trim_id=mapping.trim_id,
            pricing_platform_id=mapping.pricing_platform_id,
            slug=mapping.slug,
            config=mapping.config,
            is_active=mapping.is_active,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _trim_pricing_mapping_to_domain(model)

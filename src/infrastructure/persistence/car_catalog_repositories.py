from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.application.ports.car_catalog import (
    CarBrandRepository,
    CarModelRepository,
    CarTrimRepository,
    CarYearRepository,
)
from src.domain.entities.car_catalog import CarBrand, CarModel, CarTrim, CarYear
from src.infrastructure.persistence.models import (
    CarBrandModel,
    CarModelModel,
    CarTrimModel,
    CarYearModel,
)


def _brand_to_domain(m: CarBrandModel) -> CarBrand:
    return CarBrand(
        id=m.id,
        name=m.name,
        slug=m.slug,
        khodro45_id=m.khodro45_id,
        title_en=m.title_en,
        is_active=m.is_active,
        created_at=m.created_at,
    )


def _model_to_domain(m: CarModelModel) -> CarModel:
    return CarModel(
        id=m.id,
        brand_id=m.brand_id,
        name=m.name,
        slug=m.slug,
        khodro45_id=m.khodro45_id,
        title_en=m.title_en,
        near_threshold_pct=float(m.near_threshold_pct) if m.near_threshold_pct else 0.02,
        is_active=m.is_active,
        created_at=m.created_at,
        brand_name=m.brand.name if m.brand else None,
    )


def _year_to_domain(m: CarYearModel) -> CarYear:
    return CarYear(
        id=m.id,
        model_id=m.model_id,
        title=m.title,
        khodro45_id=m.khodro45_id,
        is_active=m.is_active,
        created_at=m.created_at,
        model_name=m.model.name if m.model else None,
        brand_name=m.model.brand.name if m.model and m.model.brand else None,
    )


def _trim_to_domain(m: CarTrimModel) -> CarTrim:
    return CarTrim(
        id=m.id,
        model_id=m.model_id,
        year_id=m.year_id,
        name=m.name,
        seo_slug=m.seo_slug,
        khodro45_id=m.khodro45_id,
        title_en=m.title_en,
        is_active=m.is_active,
        created_at=m.created_at,
        year_title=m.year.title if m.year else None,
        model_name=m.model.name if m.model else None,
        brand_name=m.model.brand.name if m.model and m.model.brand else None,
        brand_id=m.model.brand_id if m.model else None,
    )


class SqlAlchemyCarBrandRepository(CarBrandRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, brand: CarBrand) -> CarBrand:
        model = await self._session.get(CarBrandModel, brand.id)
        if model is None:
            model = CarBrandModel(
                id=brand.id or uuid4(),
                khodro45_id=brand.khodro45_id,
                name=brand.name,
                title_en=brand.title_en,
                slug=brand.slug,
                is_active=brand.is_active,
            )
            self._session.add(model)
        else:
            model.name = brand.name
            model.slug = brand.slug
            model.title_en = brand.title_en
            model.khodro45_id = brand.khodro45_id
            model.is_active = brand.is_active
        await self._session.commit()
        await self._session.refresh(model)
        return _brand_to_domain(model)

    async def get_by_id(self, brand_id: UUID) -> CarBrand | None:
        model = await self._session.get(CarBrandModel, brand_id)
        return _brand_to_domain(model) if model else None

    async def list_all(self, active_only: bool = False) -> list[CarBrand]:
        stmt = select(CarBrandModel).order_by(CarBrandModel.name)
        if active_only:
            stmt = stmt.where(CarBrandModel.is_active.is_(True))
        result = await self._session.execute(stmt)
        return [_brand_to_domain(m) for m in result.scalars().all()]


class SqlAlchemyCarModelRepository(CarModelRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, model_entity: CarModel) -> CarModel:
        model = await self._session.get(CarModelModel, model_entity.id)
        if model is None:
            model = CarModelModel(
                id=model_entity.id or uuid4(),
                khodro45_id=model_entity.khodro45_id,
                brand_id=model_entity.brand_id,
                name=model_entity.name,
                title_en=model_entity.title_en,
                slug=model_entity.slug,
                near_threshold_pct=model_entity.near_threshold_pct,
                is_active=model_entity.is_active,
            )
            self._session.add(model)
        else:
            model.name = model_entity.name
            model.slug = model_entity.slug
            model.title_en = model_entity.title_en
            model.khodro45_id = model_entity.khodro45_id
            model.near_threshold_pct = model_entity.near_threshold_pct
            model.is_active = model_entity.is_active
        await self._session.commit()
        await self._session.refresh(model)
        return _model_to_domain(model)

    async def get_by_id(self, model_id: UUID) -> CarModel | None:
        stmt = (
            select(CarModelModel)
            .options(joinedload(CarModelModel.brand))
            .where(CarModelModel.id == model_id)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _model_to_domain(model) if model else None

    async def list_all(
        self, brand_id: UUID | None = None, active_only: bool = False
    ) -> list[CarModel]:
        stmt = select(CarModelModel).options(joinedload(CarModelModel.brand))
        if brand_id:
            stmt = stmt.where(CarModelModel.brand_id == brand_id)
        if active_only:
            stmt = stmt.where(CarModelModel.is_active.is_(True))
        stmt = stmt.order_by(CarModelModel.name)
        result = await self._session.execute(stmt)
        return [_model_to_domain(m) for m in result.scalars().unique().all()]


class SqlAlchemyCarYearRepository(CarYearRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def list_by_model(self, model_id: UUID, active_only: bool = True) -> list[CarYear]:
        stmt = (
            select(CarYearModel)
            .options(joinedload(CarYearModel.model).joinedload(CarModelModel.brand))
            .where(CarYearModel.model_id == model_id)
        )
        if active_only:
            stmt = stmt.where(CarYearModel.is_active.is_(True))
        stmt = stmt.order_by(CarYearModel.title.desc())
        result = await self._session.execute(stmt)
        return [_year_to_domain(m) for m in result.scalars().unique().all()]

    async def get_by_id(self, year_id: UUID) -> CarYear | None:
        stmt = (
            select(CarYearModel)
            .options(joinedload(CarYearModel.model).joinedload(CarModelModel.brand))
            .where(CarYearModel.id == year_id)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _year_to_domain(model) if model else None


class SqlAlchemyCarTrimRepository(CarTrimRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, trim_id: UUID) -> CarTrim | None:
        stmt = (
            select(CarTrimModel)
            .options(
                joinedload(CarTrimModel.year),
                joinedload(CarTrimModel.model).joinedload(CarModelModel.brand),
            )
            .where(CarTrimModel.id == trim_id)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _trim_to_domain(model) if model else None

    async def list_by_model(
        self, model_id: UUID, *, year_id: UUID | None = None, active_only: bool = True
    ) -> list[CarTrim]:
        stmt = (
            select(CarTrimModel)
            .options(
                joinedload(CarTrimModel.year),
                joinedload(CarTrimModel.model).joinedload(CarModelModel.brand),
            )
            .where(CarTrimModel.model_id == model_id)
        )
        if year_id:
            stmt = stmt.where(CarTrimModel.year_id == year_id)
        if active_only:
            stmt = stmt.where(CarTrimModel.is_active.is_(True))
        stmt = stmt.order_by(CarTrimModel.name)
        result = await self._session.execute(stmt)
        return [_trim_to_domain(m) for m in result.scalars().unique().all()]

    async def list_active_ids(self) -> list[UUID]:
        result = await self._session.execute(
            select(CarTrimModel.id).where(CarTrimModel.is_active.is_(True))
        )
        return list(result.scalars().all())

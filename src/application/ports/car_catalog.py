from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.car_catalog import CarBrand, CarModel, CarTrim, CarYear


class CarBrandRepository(ABC):
    @abstractmethod
    async def save(self, brand: CarBrand) -> CarBrand: ...

    @abstractmethod
    async def get_by_id(self, brand_id: UUID) -> CarBrand | None: ...

    @abstractmethod
    async def list_all(self, active_only: bool = False) -> list[CarBrand]: ...


class CarModelRepository(ABC):
    @abstractmethod
    async def save(self, model: CarModel) -> CarModel: ...

    @abstractmethod
    async def get_by_id(self, model_id: UUID) -> CarModel | None: ...

    @abstractmethod
    async def list_all(self, brand_id: UUID | None = None, active_only: bool = False) -> list[CarModel]: ...


class CarYearRepository(ABC):
    @abstractmethod
    async def list_by_model(self, model_id: UUID, active_only: bool = True) -> list[CarYear]: ...

    @abstractmethod
    async def get_by_id(self, year_id: UUID) -> CarYear | None: ...


class CarTrimRepository(ABC):
    @abstractmethod
    async def get_by_id(self, trim_id: UUID) -> CarTrim | None: ...

    @abstractmethod
    async def list_by_model(
        self, model_id: UUID, *, year_id: UUID | None = None, active_only: bool = True
    ) -> list[CarTrim]: ...

    @abstractmethod
    async def list_active_ids(self) -> list[UUID]: ...

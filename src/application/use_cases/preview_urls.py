from dataclasses import dataclass
from uuid import UUID

from src.application.ports.car_catalog import CarBrandRepository, CarModelRepository, CarTrimRepository
from src.application.services.pricing_config_builder import merge_khodro45_pricing_config
from src.application.services.ensure_trim_mappings import (
    ensure_listing_mappings_for_trim,
    ensure_pricing_mapping,
)
from src.domain.exceptions import EntityNotFoundError, ValidationError
from src.domain.services.trim_production_year import resolve_production_year_range
from src.domain.services.url_builder import build_divar_search_url, build_khodro45_price_url
from src.infrastructure.config import Settings
from src.infrastructure.persistence.platform_repositories import SqlAlchemyPlatformRepository


@dataclass
class PreviewUrlsInput:
    car_trim_id: UUID
    pricing_platform_slug: str = "khodro45"
    city: str = "tehran"
    production_year_min: int | None = None
    production_year_max: int | None = None
    usage_min: int | None = None
    usage_max: int | None = None
    sample_production_year: int | None = None
    sample_kilometer: int | None = None
    color: str | None = None


@dataclass
class PreviewUrlsResult:
    divar_url: str
    pricing_url: str
    pricing_platform_slug: str
    hamrah_url: str
    khodro45_url: str | None
    divar_path: str
    khodro45_slug: str | None = None
    trim_name: str | None = None
    year_title: str | None = None


class PreviewUrlsUseCase:
    def __init__(
        self,
        car_trim_repo: CarTrimRepository,
        car_model_repo: CarModelRepository,
        car_brand_repo: CarBrandRepository,
        platform_repo: SqlAlchemyPlatformRepository,
        settings: Settings,
    ):
        self._car_trim_repo = car_trim_repo
        self._car_model_repo = car_model_repo
        self._car_brand_repo = car_brand_repo
        self._platform_repo = platform_repo
        self._settings = settings

    async def execute(self, input_dto: PreviewUrlsInput) -> PreviewUrlsResult:
        trim = await self._car_trim_repo.get_by_id(input_dto.car_trim_id)
        if not trim:
            raise EntityNotFoundError(f"Car trim {input_dto.car_trim_id} not found")

        car_model = await self._car_model_repo.get_by_id(trim.model_id)
        if not car_model:
            raise ValidationError("Car model not found")
        brand = await self._car_brand_repo.get_by_id(car_model.brand_id)
        if not brand:
            raise ValidationError("Car brand not found")

        listing_mappings = await ensure_listing_mappings_for_trim(
            self._platform_repo,
            trim=trim,
            listing_platform_slug="divar",
        )
        if not listing_mappings:
            raise ValidationError(
                "Divar listing mapping is not configured for this trim — add it at /trim-mapping"
            )
        listing_mapping = listing_mappings[0]

        year_min, year_max = resolve_production_year_range(
            trim,
            production_year_min=input_dto.production_year_min,
            production_year_max=input_dto.production_year_max,
        )

        divar_url = build_divar_search_url(
            city=input_dto.city,
            divar_path=listing_mapping.path,
            production_year_min=year_min,
            production_year_max=year_max,
            usage_min=input_dto.usage_min,
            usage_max=input_dto.usage_max,
        )

        year = input_dto.sample_production_year or year_min or year_max or 1403
        km = input_dto.sample_kilometer or input_dto.usage_max or 30000
        pricing_slug = input_dto.pricing_platform_slug

        khodro45_url = None
        khodro45_slug = None
        pricing_url = ""

        if pricing_slug == "khodro45":
            platform = await self._platform_repo.get_pricing_platform_by_slug("khodro45")
            if not platform:
                raise ValidationError("Khodro45 platform not configured")
            mapping = await ensure_pricing_mapping(
                self._platform_repo,
                trim=trim,
                pricing_platform_id=platform.id,
            )
            config = merge_khodro45_pricing_config(mapping)
            slug = config.get("slug", mapping.slug)
            color_id = config.get("default_color", "Black")
            if input_dto.color and config.get("color_map"):
                color_id = config["color_map"].get(input_dto.color, color_id)
            khodro45_slug = slug
            khodro45_url = build_khodro45_price_url(
                slug, year, km, color_id, self._settings.khodro45_base_url
            )
            pricing_url = khodro45_url
        else:
            raise ValidationError("Only Khodro45 preview is supported in 4-layer catalog")

        return PreviewUrlsResult(
            divar_url=divar_url,
            pricing_url=pricing_url,
            pricing_platform_slug=pricing_slug,
            hamrah_url="",
            khodro45_url=khodro45_url,
            divar_path=listing_mapping.path,
            khodro45_slug=khodro45_slug,
            trim_name=trim.name,
            year_title=trim.year_title,
        )

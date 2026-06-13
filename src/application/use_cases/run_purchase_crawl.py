from uuid import UUID

from src.application.ports.car_catalog import CarBrandRepository, CarModelRepository, CarTrimRepository
from src.application.ports.repositories import CrawlTargetRepository, PurchaseRequestRepository
from src.application.services.purchase_crawl_targets import attach_crawl_targets_to_purchase
from src.domain.enums.platform_fetch_strategy import PlatformFetchStrategy
from src.domain.compat import utc_now
from src.domain.exceptions import EntityNotFoundError, ValidationError
from src.infrastructure.config import Settings
from src.infrastructure.persistence.platform_repositories import SqlAlchemyPlatformRepository


class RunPurchaseCrawlUseCase:
    """Validate listing mapping and ensure crawl targets before starting a crawl."""

    def __init__(
        self,
        purchase_request_repo: PurchaseRequestRepository,
        car_trim_repo: CarTrimRepository,
        car_model_repo: CarModelRepository,
        car_brand_repo: CarBrandRepository,
        crawl_target_repo: CrawlTargetRepository,
        platform_repo: SqlAlchemyPlatformRepository,
        settings: Settings,
    ):
        self._purchase_request_repo = purchase_request_repo
        self._car_trim_repo = car_trim_repo
        self._car_model_repo = car_model_repo
        self._car_brand_repo = car_brand_repo
        self._crawl_target_repo = crawl_target_repo
        self._platform_repo = platform_repo
        self._settings = settings

    async def prepare(self, purchase_request_id: UUID) -> list[UUID]:
        purchase = await self._purchase_request_repo.get_by_id(purchase_request_id)
        if not purchase:
            raise EntityNotFoundError("Purchase request not found")
        if not purchase.is_active:
            raise ValidationError("Purchase request is not active")
        if purchase.expires_at and purchase.expires_at <= utc_now():
            raise ValidationError(
                f"Purchase request expired after {self._settings.purchase_active_days} day(s)"
            )

        trim = await self._car_trim_repo.get_by_id(purchase.car_trim_id)
        if not trim:
            raise EntityNotFoundError("Car trim not found")

        car_model = await self._car_model_repo.get_by_id(trim.model_id)
        if not car_model:
            raise ValidationError("Car model not found")

        brand = await self._car_brand_repo.get_by_id(car_model.brand_id)
        if not brand:
            raise ValidationError("Car brand not found")

        pricing_platform = None
        if purchase.pricing_platform_id:
            pricing_platform = await self._platform_repo.get_pricing_platform_by_id(
                purchase.pricing_platform_id
            )
        pricing_fetch_strategy = (
            pricing_platform.fetch_strategy
            if pricing_platform
            else PlatformFetchStrategy.CRAWL.value
        )

        if purchase.crawl_target_ids:
            return list(purchase.crawl_target_ids)

        targets, _ = await attach_crawl_targets_to_purchase(
            purchase=purchase,
            trim=trim,
            car_model=car_model,
            brand=brand,
            platform_repo=self._platform_repo,
            crawl_target_repo=self._crawl_target_repo,
            purchase_request_repo=self._purchase_request_repo,
            car_trim_repo=self._car_trim_repo,
            settings=self._settings,
            pricing_fetch_strategy=pricing_fetch_strategy,
        )
        return [t.id for t in targets]

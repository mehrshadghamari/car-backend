from src.domain.compat import StrEnum


class PlatformFetchStrategy(StrEnum):
    """How a platform supplies listing or pricing data."""

    CRAWL = "crawl"
    API = "api"

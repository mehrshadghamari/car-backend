import asyncio
from urllib.parse import urlparse

import httpx

from src.application.ports.external import DivarListingPort
from src.domain.exceptions import ExternalServiceError
from src.domain.value_objects.divar_listing import DivarListingCard, DivarListingDetail, DivarSearchPage
from src.infrastructure.adapters.divar.detail_parser import parse_post_detail
from src.infrastructure.adapters.divar.ssr_parser import parse_search_page_from_html, parse_widget_list_response
from src.infrastructure.adapters.divar.open_api_parser import parse_open_finder_response
from src.infrastructure.adapters.divar.url_converter import (
    build_divar_post_url,
    build_json_schema_from_url,
    web_url_to_api_url,
)
from src.infrastructure.config import Settings


class DivarListingAdapter(DivarListingPort):
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None):
        self._settings = settings
        self._client = client
        self._owns_client = client is None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    def _default_headers(self, referer: str) -> dict[str, str]:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/html",
            "Accept-Language": "fa-IR,fa;q=0.9",
            "Origin": "https://divar.ir",
            "Referer": referer,
        }
        headers.update(self._settings.divar_extra_headers)
        return headers

    async def fetch_search_page(
        self,
        listing_url: str,
        last_post_date_epoch: int | None = None,
    ) -> DivarSearchPage:
        client = await self._get_client()
        headers = self._default_headers(listing_url)

        if last_post_date_epoch is None:
            response = await client.get(listing_url, headers=headers, follow_redirects=True)
            if response.status_code != 200:
                raise ExternalServiceError(f"Divar SSR fetch failed: {response.status_code}")
            return parse_search_page_from_html(response.text)

        api_url, _ = web_url_to_api_url(listing_url)
        payload = {
            "json_schema": build_json_schema_from_url(listing_url),
            "last-post-date": last_post_date_epoch,
            "page": 2,
        }
        response = await client.post(
            api_url,
            json=payload,
            headers={**headers, "Content-Type": "application/json"},
        )
        if response.status_code != 200:
            raise ExternalServiceError(f"Divar API fetch failed: {response.status_code}")

        data = response.json()
        if any(w.get("widget_type") == "BLOCKING_VIEW" for w in data.get("widget_list", [])):
            return DivarSearchPage(listings=[], last_post_date_epoch=None, has_more=False)

        return parse_widget_list_response(data)

    async def fetch_listing_detail(self, token: str) -> DivarListingDetail:
        client = await self._get_client()
        url = f"https://api.divar.ir/v8/posts-v2/web/{token}"
        headers = self._default_headers(f"https://divar.ir/v/{token}")
        await asyncio.sleep(self._settings.divar_request_delay_ms / 1000)
        response = await client.get(url, headers=headers)
        if response.status_code != 200:
            raise ExternalServiceError(f"Divar detail fetch failed: {response.status_code}")
        return parse_post_detail(token, response.json())

    def build_listing_url(self, token: str) -> str:
        return build_divar_post_url(token)

    async def fetch_all_pages(
        self,
        listing_url: str,
        max_pages: int = 5,
    ) -> list[DivarListingCard]:
        all_listings: list[DivarListingCard] = []
        seen: set[str] = set()
        page = await self.fetch_search_page(listing_url)
        for card in page.listings:
            if card.token not in seen:
                seen.add(card.token)
                all_listings.append(card)

        last_epoch = page.last_post_date_epoch
        pages_fetched = 1
        while page.has_more and last_epoch and pages_fetched < max_pages:
            await asyncio.sleep(self._settings.divar_request_delay_ms / 1000)
            page = await self.fetch_search_page(listing_url, last_epoch)
            if not page.listings:
                break
            for card in page.listings:
                if card.token not in seen:
                    seen.add(card.token)
                    all_listings.append(card)
            if page.last_post_date_epoch == last_epoch:
                break
            last_epoch = page.last_post_date_epoch
            pages_fetched += 1

        return all_listings

    async def fetch_finder_posts(
        self,
        *,
        brand_model: str,
        city: str,
        category: str = "light",
        production_year_min: int | None = None,
        production_year_max: int | None = None,
        usage_min: int | None = None,
        usage_max: int | None = None,
        max_results: int = 150,
    ) -> list[DivarListingCard]:
        """Divar open-platform finder API — uses brand_model_key, not page path."""
        api_key = self._settings.divar_open_api_key
        if not api_key:
            raise ExternalServiceError("DIVAR_OPEN_API_KEY is not configured")

        brand_model = brand_model.strip()
        if not brand_model:
            raise ExternalServiceError("brand_model is required for Divar open API finder")

        query: dict = {"brand_model": [brand_model]}
        if production_year_min is not None or production_year_max is not None:
            year_filter: dict[str, str] = {}
            if production_year_min is not None:
                year_filter["min"] = str(production_year_min)
            if production_year_max is not None:
                year_filter["max"] = str(production_year_max)
            query["production_year"] = year_filter
        if usage_min is not None or usage_max is not None:
            usage_filter: dict[str, str] = {}
            if usage_min is not None:
                usage_filter["min"] = str(usage_min)
            if usage_max is not None:
                usage_filter["max"] = str(usage_max)
            query["usage"] = usage_filter

        payload = {"category": category, "city": city, "query": query}
        url = f"{self._settings.divar_open_api_base_url.rstrip('/')}/v2/open-platform/finder/post"
        client = await self._get_client()
        response = await client.post(
            url,
            json=payload,
            headers={
                "x-api-key": api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        if response.status_code != 200:
            raise ExternalServiceError(
                f"Divar open API failed: {response.status_code} — {response.text[:200]}"
            )
        cards = parse_open_finder_response(response.json())
        return cards[:max_results]

    async def close(self) -> None:
        if self._owns_client and self._client:
            await self._client.aclose()
            self._client = None

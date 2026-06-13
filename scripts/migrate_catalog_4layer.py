"""Migrate DB schema to 4-layer catalog (brand → model → year → trim)."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

from src.infrastructure.config import get_settings


def _column_exists(inspector, table: str, column: str) -> bool:
    if table not in inspector.get_table_names():
        return False
    return column in {col["name"] for col in inspector.get_columns(table)}


def _table_exists(inspector, table: str) -> bool:
    return table in inspector.get_table_names()


async def migrate() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:

        def _run(sync_conn):
            inspector = inspect(sync_conn)

            if _table_exists(inspector, "car_brands"):
                if not _column_exists(inspector, "car_brands", "khodro45_id"):
                    sync_conn.execute(text("ALTER TABLE car_brands ADD COLUMN khodro45_id INTEGER"))
                    sync_conn.execute(
                        text("CREATE UNIQUE INDEX IF NOT EXISTS ix_car_brands_k45 ON car_brands(khodro45_id)")
                    )
                if not _column_exists(inspector, "car_brands", "title_en"):
                    sync_conn.execute(text("ALTER TABLE car_brands ADD COLUMN title_en VARCHAR(100)"))

            if _table_exists(inspector, "car_models"):
                for col, typ in [
                    ("khodro45_id", "INTEGER"),
                    ("title_en", "VARCHAR(150)"),
                ]:
                    if not _column_exists(inspector, "car_models", col):
                        sync_conn.execute(text(f"ALTER TABLE car_models ADD COLUMN {col} {typ}"))

                for legacy_col in (
                    "divar_path",
                    "divar_brand_model",
                    "hamrah_brand",
                    "hamrah_model",
                    "hamrah_type_id",
                    "default_color",
                    "default_body_condition",
                    "color_map",
                    "max_pages_per_run",
                ):
                    if _column_exists(inspector, "car_models", legacy_col):
                        sync_conn.execute(text(f"ALTER TABLE car_models DROP COLUMN {legacy_col}"))

            if _table_exists(inspector, "car_model_pricing_mappings"):
                sync_conn.execute(text("DROP TABLE car_model_pricing_mappings"))

            if not _table_exists(inspector, "car_years"):
                sync_conn.execute(
                    text(
                        """
                        CREATE TABLE car_years (
                            id CHAR(36) PRIMARY KEY,
                            khodro45_id INTEGER,
                            model_id CHAR(36) NOT NULL REFERENCES car_models(id),
                            title VARCHAR(10) NOT NULL,
                            is_active BOOLEAN DEFAULT 1,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(model_id, khodro45_id)
                        )
                        """
                    )
                )
                sync_conn.execute(text("CREATE INDEX ix_car_years_model_id ON car_years(model_id)"))

            if not _table_exists(inspector, "car_trims"):
                sync_conn.execute(
                    text(
                        """
                        CREATE TABLE car_trims (
                            id CHAR(36) PRIMARY KEY,
                            khodro45_id INTEGER,
                            model_id CHAR(36) NOT NULL REFERENCES car_models(id),
                            year_id CHAR(36) NOT NULL REFERENCES car_years(id),
                            name VARCHAR(200) NOT NULL,
                            title_en VARCHAR(200),
                            seo_slug VARCHAR(200) NOT NULL,
                            is_active BOOLEAN DEFAULT 1,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(year_id, seo_slug)
                        )
                        """
                    )
                )
                sync_conn.execute(text("CREATE INDEX ix_car_trims_model_id ON car_trims(model_id)"))
                sync_conn.execute(text("CREATE INDEX ix_car_trims_seo_slug ON car_trims(seo_slug)"))

            if not _table_exists(inspector, "divar_cities"):
                sync_conn.execute(
                    text(
                        """
                        CREATE TABLE divar_cities (
                            id CHAR(36) PRIMARY KEY,
                            slug VARCHAR(80) NOT NULL UNIQUE,
                            display VARCHAR(200) NOT NULL,
                            is_active BOOLEAN DEFAULT 1
                        )
                        """
                    )
                )

            if not _table_exists(inspector, "divar_car_models"):
                sync_conn.execute(
                    text(
                        """
                        CREATE TABLE divar_car_models (
                            id CHAR(36) PRIMARY KEY,
                            slug VARCHAR(200) NOT NULL UNIQUE,
                            display VARCHAR(300) NOT NULL,
                            is_active BOOLEAN DEFAULT 1
                        )
                        """
                    )
                )

            if not _table_exists(inspector, "listing_mappings"):
                sync_conn.execute(
                    text(
                        """
                        CREATE TABLE listing_mappings (
                            id CHAR(36) PRIMARY KEY,
                            listing_platform_id CHAR(36) NOT NULL REFERENCES listing_platforms(id),
                            divar_car_model_id CHAR(36) NOT NULL REFERENCES divar_car_models(id),
                            path VARCHAR(300) NOT NULL,
                            config JSON,
                            is_active BOOLEAN DEFAULT 1
                        )
                        """
                    )
                )

            if not _table_exists(inspector, "listing_mapping_trims"):
                sync_conn.execute(
                    text(
                        """
                        CREATE TABLE listing_mapping_trims (
                            id CHAR(36) PRIMARY KEY,
                            listing_mapping_id CHAR(36) NOT NULL REFERENCES listing_mappings(id),
                            trim_id CHAR(36) NOT NULL REFERENCES car_trims(id),
                            UNIQUE(listing_mapping_id, trim_id)
                        )
                        """
                    )
                )

            if not _table_exists(inspector, "trim_pricing_mappings"):
                sync_conn.execute(
                    text(
                        """
                        CREATE TABLE trim_pricing_mappings (
                            id CHAR(36) PRIMARY KEY,
                            trim_id CHAR(36) NOT NULL REFERENCES car_trims(id),
                            pricing_platform_id CHAR(36) NOT NULL REFERENCES pricing_platforms(id),
                            slug VARCHAR(200) NOT NULL,
                            config JSON,
                            is_active BOOLEAN DEFAULT 1,
                            UNIQUE(trim_id, pricing_platform_id)
                        )
                        """
                    )
                )

            if _table_exists(inspector, "purchase_requests"):
                if not _column_exists(inspector, "purchase_requests", "car_trim_id"):
                    sync_conn.execute(
                        text("ALTER TABLE purchase_requests ADD COLUMN car_trim_id CHAR(36) REFERENCES car_trims(id)")
                    )
                    sync_conn.execute(
                        text("CREATE INDEX IF NOT EXISTS ix_purchase_requests_car_trim_id ON purchase_requests(car_trim_id)")
                    )

            if _table_exists(inspector, "crawl_targets"):
                if not _column_exists(inspector, "crawl_targets", "listing_mapping_id"):
                    sync_conn.execute(
                        text(
                            "ALTER TABLE crawl_targets ADD COLUMN listing_mapping_id "
                            "CHAR(36) REFERENCES listing_mappings(id)"
                        )
                    )

            if _table_exists(inspector, "market_prices"):
                if not _column_exists(inspector, "market_prices", "trim_id"):
                    sync_conn.execute(
                        text("ALTER TABLE market_prices ADD COLUMN trim_id CHAR(36) REFERENCES car_trims(id)")
                    )

        await conn.run_sync(_run)

    await engine.dispose()
    print(f"4-layer catalog migration complete: {settings.database_url}")


if __name__ == "__main__":
    asyncio.run(migrate())

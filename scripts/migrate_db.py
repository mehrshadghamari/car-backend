"""Apply lightweight schema updates to an existing SQLite/Postgres DB."""
import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

from src.infrastructure.config import get_settings


def _column_exists(inspector, table: str, column: str) -> bool:
    return column in {col["name"] for col in inspector.get_columns(table)}


async def migrate() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        def _migrate(sync_conn):
            inspector = inspect(sync_conn)
            tables = inspector.get_table_names()

            if "crawl_runs" in tables:
                crawl_cols = {col["name"] for col in inspector.get_columns("crawl_runs")}
                if "diagnostics" not in crawl_cols:
                    sync_conn.execute(text("ALTER TABLE crawl_runs ADD COLUMN diagnostics JSON"))

            if "crawl_targets" in tables:
                if not _column_exists(inspector, "crawl_targets", "car_model_id"):
                    sync_conn.execute(
                        text(
                            "ALTER TABLE crawl_targets ADD COLUMN car_model_id "
                            "CHAR(36) REFERENCES car_models(id)"
                        )
                    )
                if not _column_exists(inspector, "crawl_targets", "city"):
                    sync_conn.execute(
                        text("ALTER TABLE crawl_targets ADD COLUMN city VARCHAR(50) DEFAULT 'tehran'")
                    )
                if not _column_exists(inspector, "crawl_targets", "is_shared_pool"):
                    sync_conn.execute(
                        text(
                            "ALTER TABLE crawl_targets ADD COLUMN is_shared_pool "
                            "BOOLEAN DEFAULT false NOT NULL"
                        )
                    )

            if "listings" in tables:
                if not _column_exists(inspector, "listings", "car_model_id"):
                    sync_conn.execute(
                        text(
                            "ALTER TABLE listings ADD COLUMN car_model_id "
                            "CHAR(36) REFERENCES car_models(id)"
                        )
                    )
                if not _column_exists(inspector, "listings", "is_active"):
                    sync_conn.execute(
                        text(
                            "ALTER TABLE listings ADD COLUMN is_active "
                            "BOOLEAN DEFAULT true NOT NULL"
                        )
                    )

            if "opportunities" not in tables:
                return

            columns = {col["name"] for col in inspector.get_columns("opportunities")}
            if "price_basis" not in columns:
                sync_conn.execute(
                    text(
                        "ALTER TABLE opportunities ADD COLUMN price_basis VARCHAR(10) "
                        "NOT NULL DEFAULT 'down'"
                    )
                )
            if "reference_price" not in columns:
                sync_conn.execute(
                    text("ALTER TABLE opportunities ADD COLUMN reference_price BIGINT")
                )
                sync_conn.execute(
                    text(
                        "UPDATE opportunities SET reference_price = market_price_down "
                        "WHERE reference_price IS NULL"
                    )
                )
            if "market_price_mid" not in columns:
                sync_conn.execute(
                    text("ALTER TABLE opportunities ADD COLUMN market_price_mid BIGINT")
                )
            if "deal_tag" not in columns:
                sync_conn.execute(
                    text(
                        "ALTER TABLE opportunities ADD COLUMN deal_tag VARCHAR(10) "
                        "NOT NULL DEFAULT 'best'"
                    )
                )
                sync_conn.execute(
                    text(
                        "UPDATE opportunities SET deal_tag = 'best' "
                        "WHERE price_basis = 'down' OR price_basis IS NULL"
                    )
                )
                sync_conn.execute(
                    text(
                        "UPDATE opportunities SET deal_tag = 'good' "
                        "WHERE price_basis = 'mid' AND is_below_floor = true"
                    )
                )
                sync_conn.execute(
                    text(
                        "UPDATE opportunities SET deal_tag = 'fair' "
                        "WHERE price_basis = 'mid' AND is_below_floor = false"
                    )
                )

            if "purchase_request_id" not in columns:
                sync_conn.execute(
                    text(
                        "ALTER TABLE opportunities ADD COLUMN purchase_request_id "
                        "CHAR(36) REFERENCES purchase_requests(id)"
                    )
                )
                sync_conn.execute(
                    text(
                        """
                        UPDATE opportunities
                        SET purchase_request_id = (
                            SELECT pr.id FROM purchase_requests pr
                            WHERE pr.crawl_target_id = opportunities.crawl_target_id
                            LIMIT 1
                        )
                        WHERE purchase_request_id IS NULL
                        """
                    )
                )

            if "crawl_targets" in tables and "purchase_requests" in tables:
                sync_conn.execute(
                    text(
                        """
                        UPDATE crawl_targets
                        SET car_model_id = (
                            SELECT pr.car_model_id FROM purchase_requests pr
                            WHERE pr.crawl_target_id = crawl_targets.id
                            LIMIT 1
                        ),
                        city = COALESCE(
                            (SELECT pr.city FROM purchase_requests pr
                             WHERE pr.crawl_target_id = crawl_targets.id LIMIT 1),
                            city,
                            'tehran'
                        ),
                        is_shared_pool = true
                        WHERE is_shared_pool = false
                          AND car_model_id IS NULL
                          AND id IN (SELECT crawl_target_id FROM purchase_requests)
                        """
                    )
                )

            if "listing_platforms" in tables:
                if not _column_exists(inspector, "listing_platforms", "fetch_strategy"):
                    sync_conn.execute(
                        text(
                            "ALTER TABLE listing_platforms ADD COLUMN fetch_strategy "
                            "VARCHAR(10) DEFAULT 'crawl' NOT NULL"
                        )
                    )
                sync_conn.execute(
                    text(
                        "UPDATE listing_platforms SET fetch_strategy = 'api' WHERE slug = 'divar'"
                    )
                )

            if "pricing_platforms" in tables:
                if not _column_exists(inspector, "pricing_platforms", "fetch_strategy"):
                    sync_conn.execute(
                        text(
                            "ALTER TABLE pricing_platforms ADD COLUMN fetch_strategy "
                            "VARCHAR(10) DEFAULT 'crawl' NOT NULL"
                        )
                    )

            if "crawl_targets" in tables:
                if not _column_exists(inspector, "crawl_targets", "pool_production_year"):
                    sync_conn.execute(
                        text(
                            "ALTER TABLE crawl_targets ADD COLUMN pool_production_year INTEGER"
                        )
                    )
                sync_conn.execute(
                    text("DROP INDEX IF EXISTS uq_shared_pool_mapping_city_source")
                )
                sync_conn.execute(
                    text(
                        """
                        CREATE UNIQUE INDEX IF NOT EXISTS uq_shared_pool_mapping_city_source_year
                        ON crawl_targets(
                            listing_mapping_id,
                            city,
                            source,
                            COALESCE(pool_production_year, -1)
                        )
                        WHERE is_shared_pool = true AND listing_mapping_id IS NOT NULL
                        """
                    )
                )

            if "divar_cities" not in tables:
                sync_conn.execute(
                    text(
                        """
                        CREATE TABLE divar_cities (
                            id CHAR(36) PRIMARY KEY,
                            slug VARCHAR(80) NOT NULL UNIQUE,
                            display VARCHAR(200) NOT NULL,
                            is_active BOOLEAN DEFAULT true
                        )
                        """
                    )
                )
                sync_conn.execute(
                    text("CREATE INDEX ix_divar_cities_slug ON divar_cities(slug)")
                )

            if "divar_car_models" not in tables:
                sync_conn.execute(
                    text(
                        """
                        CREATE TABLE divar_car_models (
                            id CHAR(36) PRIMARY KEY,
                            slug VARCHAR(200) NOT NULL UNIQUE,
                            display VARCHAR(300) NOT NULL,
                            is_active BOOLEAN DEFAULT true
                        )
                        """
                    )
                )
                sync_conn.execute(
                    text("CREATE INDEX ix_divar_car_models_slug ON divar_car_models(slug)")
                )

            if "listing_mappings" in tables:
                listing_cols = {col["name"] for col in inspector.get_columns("listing_mappings")}
                if "divar_car_model_id" not in listing_cols:
                    sync_conn.execute(
                        text(
                            "ALTER TABLE listing_mappings ADD COLUMN divar_car_model_id CHAR(36) "
                            "REFERENCES divar_car_models(id)"
                        )
                    )
                if "brand_model_key" in listing_cols:
                    rows = sync_conn.execute(
                        text(
                            "SELECT id, brand_model_key FROM listing_mappings "
                            "WHERE divar_car_model_id IS NULL"
                        )
                    ).fetchall()
                    for mapping_id, brand_key in rows:
                        brand_key = (brand_key or "").strip()
                        if not brand_key:
                            continue
                        existing = sync_conn.execute(
                            text("SELECT id FROM divar_car_models WHERE slug = :slug"),
                            {"slug": brand_key},
                        ).fetchone()
                        if existing:
                            divar_model_id = existing[0]
                        else:
                            divar_model_id = str(uuid.uuid4())
                            sync_conn.execute(
                                text(
                                    "INSERT INTO divar_car_models (id, slug, display, is_active) "
                                    "VALUES (:id, :slug, :display, true)"
                                ),
                                {
                                    "id": divar_model_id,
                                    "slug": brand_key,
                                    "display": brand_key,
                                },
                            )
                        sync_conn.execute(
                            text(
                                "UPDATE listing_mappings SET divar_car_model_id = :model_id "
                                "WHERE id = :mapping_id"
                            ),
                            {"model_id": divar_model_id, "mapping_id": mapping_id},
                        )
                    listing_cols = {col["name"] for col in inspector.get_columns("listing_mappings")}
                    if "brand_model_key" in listing_cols:
                        sync_conn.execute(
                            text("ALTER TABLE listing_mappings DROP COLUMN brand_model_key")
                        )
                    listing_cols = {col["name"] for col in inspector.get_columns("listing_mappings")}
                    if "default_city" in listing_cols:
                        sync_conn.execute(
                            text("ALTER TABLE listing_mappings DROP COLUMN default_city")
                        )

        await conn.run_sync(_migrate)

    await engine.dispose()
    print(f"Migration complete: {settings.database_url}")
    print("Tip: run python3 scripts/dedupe_shared_pools.py if duplicate shared pools exist.")


if __name__ == "__main__":
    asyncio.run(migrate())

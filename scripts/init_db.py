"""Create all tables (SQLite or PostgreSQL). Run: PYTHONPATH=src python3 scripts/init_db.py"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.ext.asyncio import create_async_engine

from src.infrastructure.config import get_settings
from src.infrastructure.persistence.models import Base


async def init_db() -> None:
    settings = get_settings()
    url = settings.database_url
    if url.startswith("sqlite"):
        Path("./data").mkdir(exist_ok=True)

    engine = create_async_engine(url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print(f"Database initialized: {url}")


if __name__ == "__main__":
    asyncio.run(init_db())

"""Isolated DB sessions for Celery / FastAPI background tasks (separate event loop)."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.infrastructure.config import get_settings


@asynccontextmanager
async def task_db_session() -> AsyncGenerator[AsyncSession, None]:
    settings = get_settings()
    connect_args = (
        {"check_same_thread": False} if "sqlite" in settings.database_url else {}
    )
    engine = create_async_engine(
        settings.database_url,
        connect_args=connect_args,
    )
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with factory() as session:
            yield session
    finally:
        await engine.dispose()

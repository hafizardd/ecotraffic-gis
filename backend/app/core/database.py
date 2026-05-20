from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as SyncSession
from contextlib import contextmanager

# ------------------------------------------------------------------
# Base — all models inherit from this.
# Defined here at module level so Alembic can import it without
# triggering engine creation.
# ------------------------------------------------------------------

class Base(DeclarativeBase):
    pass

# ------------------------------------------------------------------
# Get Synchronous engine and session for Alembic migrations
# ------------------------------------------------------------------

_sync_engine = None

def get_sync_engine():
    global _sync_engine
    if _sync_engine is None:
        _sync_engine = create_engine(
            settings.DATABASE_URL_SYNC,
            pool_pre_ping=True,
        )
    return _sync_engine

@contextmanager
def get_sync_db():
    SessionLocal = sessionmaker(bind=get_sync_engine())
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

# ------------------------------------------------------------------
# Lazy engine + session factory.
# Not created at import time — only when get_engine() is first called.
# This prevents the asyncpg/psycopg2 conflict when Alembic imports Base.
# ------------------------------------------------------------------

_engine = None
_AsyncSessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory():
    global _AsyncSessionLocal
    if _AsyncSessionLocal is None:
        _AsyncSessionLocal = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _AsyncSessionLocal


# ------------------------------------------------------------------
# FastAPI dependency — yields a session per request, always closes it
# ------------------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
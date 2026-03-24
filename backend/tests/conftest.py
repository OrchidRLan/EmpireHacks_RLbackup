"""Root conftest.py — shared fixtures for all test modules.

SQLite compatibility strategy
------------------------------
Production models use ``sqlalchemy.dialects.postgresql.ARRAY(String)`` for
list-of-string columns.  SQLite (aiosqlite) has no ARRAY type.  We patch
those column types to ``_JsonList`` (a ``TypeDecorator`` backed by plain
``String`` / JSON serialisation) *before* SQLAlchemy processes the table
metadata, so that ``Base.metadata.create_all`` produces valid SQLite DDL.

Lifespan suppression
---------------------
The FastAPI ``lifespan`` starts an APScheduler job and calls
``create_all_tables``.  During tests we want neither, so we patch the
lifespan to a no-op.  Tables are created once by the session-scoped
``create_tables`` fixture instead.

Isolation strategy
-------------------
Each test gets its own ``db_session`` backed by a real in-memory SQLite
connection.  A transaction is started at the beginning of the fixture and
rolled back at the end so tests never bleed state into each other.
"""

import json
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import String, TypeDecorator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# ── 1. Environment (before any app import) ────────────────────────────────────

os.environ.setdefault("ANTHROPIC_API_KEY", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SMTP_HOST", "localhost")
os.environ.setdefault("SMTP_PORT", "0")
os.environ.setdefault("SMTP_USER", "")
os.environ.setdefault("SMTP_PASSWORD", "")

# ── 2. Patch ARRAY columns before model classes are loaded ────────────────────

class _JsonList(TypeDecorator):
    """Stores a Python list as a JSON string in SQLite; transparent on read."""

    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return "[]"
        if isinstance(value, str):
            return value  # already serialised
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return []
        if isinstance(value, list):
            return value
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []


def _patch_array_columns() -> None:
    """Replace ARRAY(String) column types with _JsonList for all model tables."""
    import importlib
    from sqlalchemy.dialects.postgresql import ARRAY

    for mod_name in ("app.models.apartment", "app.models.preferences"):
        mod = importlib.import_module(mod_name)
        for obj in vars(mod).values():
            if not isinstance(obj, type):
                continue
            table = getattr(obj, "__table__", None)
            if table is None:
                continue
            for col in table.columns:
                if isinstance(col.type, ARRAY):
                    col.type = _JsonList()


_patch_array_columns()

# ── 3. Import application (after patching, before engine creation) ────────────

import app.models  # noqa: F401, E402 — side-effect: registers all ORM classes
from app.database import Base, get_db  # noqa: E402

# ── 4. In-memory SQLite async engine (session-scoped) ─────────────────────────

_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

# ``check_same_thread=False`` is required for aiosqlite
_test_engine = create_async_engine(
    _TEST_DB_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

_TestSessionFactory = async_sessionmaker(
    _test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ── 5. Create tables once per session ─────────────────────────────────────────

@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    """DDL: create all tables once before any test runs; drop after session."""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ── 6. Per-test database session with rollback isolation ──────────────────────

@pytest_asyncio.fixture()
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a transactional AsyncSession; rolls back after each test.

    We use a plain SQLAlchemy connection with an explicit ``begin()`` so we
    can roll back the entire test's writes without touching any other test.
    SQLite in-memory databases are shared within the same engine, so rollback
    gives us clean isolation without wiping and re-creating tables.
    """
    async with _test_engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await conn.rollback()


# ── 7. FastAPI AsyncClient with injected test DB ──────────────────────────────

@pytest_asyncio.fixture()
async def test_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Yield an httpx AsyncClient whose requests hit the FastAPI app.

    - Overrides ``get_db`` to use the test session.
    - Suppresses the real lifespan (APScheduler + create_all_tables) with a
      no-op so tests don't start background jobs or touch the prod DB.
    """
    from app.main import app as fastapi_app

    async def _override_get_db():
        yield db_session

    @asynccontextmanager
    async def _noop_lifespan(application):
        yield

    fastapi_app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=fastapi_app)
    with patch.object(fastapi_app.router, "lifespan_context", _noop_lifespan):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    fastapi_app.dependency_overrides.clear()

"""
SecureNet Backend — Database Base Configuration
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.core.config import settings

_engine_kwargs = {"echo": settings.DEBUG}
if not settings.DATABASE_URL.startswith("sqlite"):
    # SQLite (used by the test-suite) does not accept queue-pool sizing.
    # The cloud database is far away (~300 ms per round trip), so no extra
    # "pre-ping" round trip per request. Instead connections are replaced
    # after 4 minutes, before Neon's 5-minute idle suspend can close them.
    _engine_kwargs.update(
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_pre_ping=False,
        pool_recycle=240,
    )

# Create async engine
engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Base class for all models
Base = declarative_base()


async def get_db():
    """Dependency for getting async database sessions"""
    async with AsyncSessionLocal() as session:
        yield session

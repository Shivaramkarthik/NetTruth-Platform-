try:
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
    from sqlalchemy.orm import DeclarativeBase
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    # Mock classes to avoid NameError
    class AsyncSession: pass
    class DeclarativeBase: pass
    def create_async_engine(*args, **kwargs): return None
    def async_sessionmaker(*args, **kwargs): return None

from app.config import settings


if DB_AVAILABLE:
    class Base(DeclarativeBase):
        """Base class for all database models."""
        pass

    # Create async engine arguments based on DB type
    engine_args = {"echo": settings.DEBUG}
    if "sqlite" not in settings.DATABASE_URL:
        engine_args.update({
            "pool_pre_ping": True,
            "pool_size": 10,
            "max_overflow": 20
        })

    engine = create_async_engine(settings.DATABASE_URL, **engine_args)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
else:
    class Base: pass
    engine = None
    async_session = None


async def get_db():
    """Mock dependency to get database session."""
    if not DB_AVAILABLE:
        yield None
        return
        
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables (skipped if DB not available)."""
    if not DB_AVAILABLE or engine is None:
        return
        
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

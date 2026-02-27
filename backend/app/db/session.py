"""SQLAlchemy Async Engine + SessionFactory Singleton.

Erstellt eine einzelne async Engine-Instanz die von allen
Repositories geteilt wird.
"""

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config.settings import Settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine(settings: Settings) -> AsyncEngine:
    """Gibt die async Engine Singleton-Instanz zurueck.

    Erstellt die Engine beim ersten Aufruf mit den Settings.
    """
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.async_database_url,
            echo=settings.db_echo,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
        )
    return _engine


def get_session_factory(settings: Settings) -> async_sessionmaker[AsyncSession]:
    """Gibt die SessionFactory Singleton-Instanz zurueck.

    Erstellt Engine und Factory beim ersten Aufruf.
    """
    global _session_factory
    if _session_factory is None:
        engine = get_engine(settings)
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def dispose_engine() -> None:
    """Schliesst die Engine und gibt alle Connections frei."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None


def reset_db() -> None:
    """Setzt Engine und SessionFactory zurueck (fuer Tests)."""
    global _engine, _session_factory
    _engine = None
    _session_factory = None

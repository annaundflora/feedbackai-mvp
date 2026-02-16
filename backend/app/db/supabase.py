"""Supabase Client Singleton.

Erstellt eine einzelne Supabase-Client-Instanz die von allen
Repositories geteilt wird. Konfiguriert mit DB_TIMEOUT_SECONDS.
"""
from supabase import Client, create_client

from app.config.settings import Settings

_supabase_client: Client | None = None


def get_supabase_client(settings: Settings) -> Client:
    """Gibt den Supabase Client Singleton zurueck.

    Erstellt den Client beim ersten Aufruf mit den Settings.
    Nachfolgende Aufrufe geben dieselbe Instanz zurueck.

    Args:
        settings: Pydantic Settings mit SUPABASE_URL und SUPABASE_KEY.

    Returns:
        Konfigurierter Supabase Client.
    """
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(
            settings.supabase_url,
            settings.supabase_key,
            options=_build_client_options(settings),
        )
    return _supabase_client


def _build_client_options(settings: Settings):
    """Erstellt ClientOptions mit Timeout-Konfiguration.

    Args:
        settings: Pydantic Settings mit db_timeout_seconds.

    Returns:
        ClientOptions mit konfiguriertem Timeout.
    """
    from supabase.lib.client_options import ClientOptions

    timeout = settings.db_timeout_seconds
    opts = ClientOptions(
        postgrest_client_timeout=timeout,
    )
    # supabase v2.28 bug: Client expects attrs missing from ClientOptions
    for attr in ("storage", "httpx_client"):
        if not hasattr(opts, attr):
            setattr(opts, attr, None)
    return opts


def reset_supabase_client() -> None:
    """Setzt den Client-Singleton zurueck (fuer Tests)."""
    global _supabase_client
    _supabase_client = None

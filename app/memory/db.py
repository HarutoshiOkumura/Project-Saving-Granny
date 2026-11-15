"""The only module that talks to Supabase. Every call goes through `rpc(name, params)`."""

import asyncio
from uuid import UUID

from supabase import AsyncClient, AsyncClientOptions, acreate_client

from app.config import get_settings
from app.memory.schema import Channel, FindResult, PerceptionContext

READ_TIMEOUT_S = 2.0

_client: AsyncClient | None = None
_client_lock = asyncio.Lock()


async def _get_client() -> AsyncClient:
    """One client per process, built on first use from the secret key (backend only)."""
    global _client
    async with _client_lock:
        if _client is None:
            settings = get_settings()
            _client = await acreate_client(
                settings.supabase_url,
                settings.supabase_secret_key.get_secret_value(),
                options=AsyncClientOptions(
                    auto_refresh_token=False,
                    persist_session=False,
                    postgrest_client_timeout=READ_TIMEOUT_S,
                ),
            )
    return _client


async def ask_item(query: str, channel: Channel) -> FindResult:
    """Answer "where is it?" and log the question, in one round trip.

    Raises TimeoutError after READ_TIMEOUT_S, the client's errors on a failed call, and
    pydantic.ValidationError if the answer does not fit FindResult. Callers fall back.
    """
    params = {"p_home": str(get_settings().home_id), "p_query": query, "p_channel": channel}
    async with asyncio.timeout(READ_TIMEOUT_S):
        client = await _get_client()
        response = await client.rpc("ask_item", params).execute()
    return FindResult.model_validate(response.data)


async def perception_context(room_id: UUID | None = None) -> PerceptionContext:
    """What the vision model may answer with (rooms, landmarks, items) and the current beliefs.

    With `room_id`, landmarks are limited to that room and the rooms linked to it. No-capture
    rooms are listed in `rooms` but have no landmarks. Raises like `ask_item`.
    """
    params = {"p_home": str(get_settings().home_id), "p_room": str(room_id) if room_id else None}
    async with asyncio.timeout(READ_TIMEOUT_S):
        client = await _get_client()
        response = await client.rpc("perception_context", params).execute()
    return PerceptionContext.model_validate(response.data)

"""Signed links to crops, cached for most of their hour (D17: crops are signed for 1 hour).

The dashboard polls every 2 seconds (D16): without the cache every poll would sign every crop
again, and a fresh link would make the browser fetch the picture again. The same storage path
keeps the same link for CACHE_S, so the page can keep its <img> until the photo itself changes.
"""

import time

from app.memory import db

CACHE_S = 50 * 60  # links last 3600 s (db.PHOTO_LINK_S); stop handing one out 10 minutes early

_cache: dict[str, tuple[str, float]] = {}


async def links(paths: list[str]) -> dict[str, str]:
    """Storage path to signed link, for every path whose file exists. Raises like db.sign_photos
    when new links are needed and signing fails."""
    now = time.monotonic()
    wanted = set(paths)
    missing = [p for p in wanted if p not in _cache or now - _cache[p][1] >= CACHE_S]
    if missing:
        signed = await db.sign_photos(missing)
        for path, url in signed.items():
            _cache[path] = (url, now)
    return {p: _cache[p][0] for p in wanted if p in _cache and now - _cache[p][1] < CACHE_S}


def clear() -> None:
    _cache.clear()

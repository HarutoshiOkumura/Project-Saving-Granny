"""Rebuild the Typesense `moments` collection from Supabase: every stay of an enrolled item, with
a vector made from its photo and words (app/moments.py).

The ingest worker keeps the copy current as sightings arrive. Run this after starting a fresh
Typesense, after the rehearsal reset, or when the copy looks wrong. Safe to run repeatedly; it
makes one Gemini embedding call per stay that has a photo:

    uv run python -m scripts.sync_moments
"""

import asyncio

from app import moments


async def main() -> None:
    count = await moments.sync()
    print(f"Typesense collection {moments.COLLECTION!r}: {count} moments")


if __name__ == "__main__":
    asyncio.run(main())

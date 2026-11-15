"""Copy this home's item names and aliases from Supabase to Typesense (step 09).

Run it after the seed and whenever items or aliases change. Safe to run repeatedly:

    uv run python -m scripts.sync_typesense
"""

import asyncio

from app import names
from app.memory import db


async def main() -> None:
    items = await db.list_items()
    count = await names.sync(items)
    listed = ", ".join(i.name for i in items)
    print(f"Typesense collection {names.COLLECTION!r}: {count} items ({listed})")


if __name__ == "__main__":
    asyncio.run(main())

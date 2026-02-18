"""Seed the loads collection with mock data from data/seed_loads.json.

Replaces all existing loads — safe to re-run since the data is mock/sample data.

Usage: .venv/bin/python scripts/seed_db.py
"""

import asyncio
import json
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings

SEED_FILE = Path(__file__).resolve().parent.parent / "data" / "seed_loads.json"


async def seed():
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.DATABASE_NAME]

    with open(SEED_FILE) as f:
        loads = json.load(f)

    await db.loads.delete_many({})  # destructive: wipes all existing loads
    result = await db.loads.insert_many(loads)
    print(f"Seeded {len(result.inserted_ids)} loads into '{settings.DATABASE_NAME}'")

    client.close()


if __name__ == "__main__":
    asyncio.run(seed())

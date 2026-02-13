import asyncio
import json
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings

SEED_FILE = Path(__file__).resolve().parent.parent / "data" / "seed_loads.json"


async def seed():
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]

    with open(SEED_FILE) as f:
        loads = json.load(f)

    await db.loads.delete_many({})
    result = await db.loads.insert_many(loads)
    print(f"Seeded {len(result.inserted_ids)} loads into '{settings.DATABASE_NAME}'")

    client.close()


if __name__ == "__main__":
    asyncio.run(seed())

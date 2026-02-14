from typing import Optional

from app.database import get_database


async def ingest_call_record(record: dict) -> str:
    """Upsert a call record into MongoDB. Returns 'created' or 'updated'."""
    db = get_database()
    call_id = record["system"]["call_id"]

    result = await db.call_records.update_one(
        {"system.call_id": call_id},
        {"$set": record},
        upsert=True,
    )

    return "created" if result.upserted_id else "updated"

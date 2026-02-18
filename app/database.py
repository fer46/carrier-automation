"""MongoDB connection lifecycle management.

Uses a module-level singleton client. Call connect_db() at app startup
(via the FastAPI lifespan) before using get_database().
"""

from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings

client: Optional[AsyncIOMotorClient] = None


def get_database() -> AsyncIOMotorDatabase:
    if client is None:
        raise RuntimeError("Database client is not initialized. Call connect_db() first.")
    return client[settings.DATABASE_NAME]


async def connect_db() -> None:
    global client
    client = AsyncIOMotorClient(settings.MONGODB_URI)


async def disconnect_db() -> None:
    global client
    if client:
        client.close()
        client = None

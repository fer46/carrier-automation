import hmac

from fastapi import Header, HTTPException

from app.config import settings


async def verify_api_key(x_api_key: str = Header(...)) -> str:
    # Use constant-time comparison to prevent timing attacks.
    if not hmac.compare_digest(x_api_key, settings.API_KEY):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key

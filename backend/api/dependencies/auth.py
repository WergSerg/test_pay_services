from fastapi import Header, HTTPException, status, Depends
from typing import Optional

from backend.core.config import settings


async def verify_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")) -> str:
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key header is required"
        )

    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )
    return x_api_key

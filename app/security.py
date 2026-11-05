"""Single trusted workspace authentication. project_id is a label, not a tenant boundary."""

import secrets

from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader

from app import config

header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def check_key(key: str | None = Depends(header)):
    if config.API_KEY and not secrets.compare_digest(key or "", config.API_KEY):
        raise HTTPException(401, "Invalid or missing API key")
    return key or "anonymous"

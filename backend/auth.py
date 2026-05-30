import os
import secrets
from fastapi import Header, HTTPException

def verify_api_key(x_api_key: str = Header(None)) -> bool:
    """Verify X-API-Key header using timing-safe comparison."""
    required_key = os.getenv("AGENTWATCH_API_KEY")
    if required_key:
        if not x_api_key:
            raise HTTPException(status_code=401, detail="Unauthorized: Missing API Key")
        # Use secrets.compare_digest to prevent timing attacks
        # Encode to bytes to handle non-ASCII characters
        if not secrets.compare_digest(x_api_key.encode('utf-8'), required_key.encode('utf-8')):
            raise HTTPException(status_code=401, detail="Unauthorized: Invalid API Key")
    return True

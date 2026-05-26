import os
from fastapi import Header, HTTPException

def verify_api_key(x_api_key: str = Header(None)):
    required_key = os.getenv("AGENTWATCH_API_KEY")
    if required_key:
        if not x_api_key or x_api_key != required_key:
            raise HTTPException(status_code=401, detail="Unauthorized")
    return True

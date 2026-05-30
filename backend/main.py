from datetime import datetime
import asyncio
import json
import logging
import os
import secrets
from typing import List, Optional, Any, Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy.sql import text

from db import (
    init_db, get_db, insert_run, insert_spans_batch, get_runs, get_run_details, update_run_status, async_session
)
from otlp import decode_otlp_request
from auth import verify_api_key

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agentwatch.main")

app = FastAPI(title="AgentWatch Backend", version="1.0.0")

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration with production warning
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
if "*" in ALLOWED_ORIGINS:
    logger.warning(
        "SECURITY WARNING: CORS is configured to allow all origins (*). "
        "Set ALLOWED_ORIGINS environment variable for production (e.g., ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com)"
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler to sanitize error messages
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    # Don't leak internal error details to clients
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please contact support if the issue persists."
        }
    )

# Helper to recursively convert datetime objects to ISO strings for WebSocket serialization
def serialize_datetimes(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: serialize_datetimes(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [serialize_datetimes(v) for v in data]
    elif isinstance(data, datetime):
        return data.isoformat()
    return data

# WebSocket authentication helper
async def verify_websocket_api_key(websocket: WebSocket) -> bool:
    """Verify X-API-Key header during WebSocket handshake."""
    required_key = os.getenv("AGENTWATCH_API_KEY")
    if not required_key:
        return True  # No auth required if key not set

    # Extract API key from headers
    api_key = websocket.headers.get("x-api-key")
    if not api_key:
        logger.warning("WebSocket connection rejected: Missing X-API-Key header")
        return False

    # Use timing-safe comparison
    if not secrets.compare_digest(api_key, required_key):
        logger.warning("WebSocket connection rejected: Invalid X-API-Key")
        return False

    return True

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New WebSocket client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Remaining: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        # Convert any datetime objects in the message dict to ISO strings first
        serialized_msg = serialize_datetimes(message)
        
        dead = []
        for connection in self.active_connections:
            try:
                await connection.send_json(serialized_msg)
            except Exception as e:
                logger.warning(f"Error sending message to WebSocket client: {e}")
                dead.append(connection)
        for conn in dead:
            self.disconnect(conn)

manager = ConnectionManager()

# Pydantic Schemas
class RunCreate(BaseModel):
    run_id: str
    name: str
    session_id: Optional[str] = None
    tags: List[str] = []
    started_at: str
    metadata: dict = {}

class RunUpdate(BaseModel):
    status: str
    ended_at: Optional[str] = None
    error_message: Optional[str] = None

class SpanCreate(BaseModel):
    span_id: str
    run_id: str
    parent_span_id: Optional[str] = None
    span_type: str = Field(default="llm")
    name: str
    model: Optional[str] = None
    provider: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    input_preview: Optional[str] = None
    output_preview: Optional[str] = None
    started_at: str
    ended_at: Optional[str] = None
    status: str = "running"
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    tool_name: Optional[str] = None
    tool_input: Optional[Any] = None
    tool_output: Optional[Any] = None
    metadata: dict = {}

class SpanBatch(BaseModel):
    spans: List[SpanCreate]

# Startup Tasks
@app.on_event("startup")
async def startup_event():
    logger.info("Initializing AgentWatch Database...")
    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            await init_db()
            logger.info("Database initialized successfully.")
            return
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Database init failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"Database initialization failed after {max_retries} attempts: {e}")
                raise

# Health Check
@app.get("/health", status_code=200)
async def health():
    """Health check with database connectivity verification."""
    try:
        # Verify database connectivity
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ok", "version": "1.0.0", "time": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

# Runs Endpoints
@app.post("/v1/runs", dependencies=[Depends(verify_api_key)])
async def create_run(run: RunCreate, db = Depends(get_db)):
    run_dict = run.model_dump()
    await insert_run(db, run_dict)
    
    # Broadcast event
    await manager.broadcast({"type": "run_started", "data": run_dict})
    return {"data": {"run_id": run.run_id, "status": "running"}}

@app.patch("/v1/runs/{run_id}", dependencies=[Depends(verify_api_key)])
async def update_run(run_id: str, update: RunUpdate, db = Depends(get_db)):
    updated_run = await update_run_status(
        db, 
        run_id=run_id, 
        status=update.status, 
        ended_at=update.ended_at, 
        error_message=update.error_message
    )
    if not updated_run:
        raise HTTPException(status_code=404, detail=f"Run with ID {run_id} not found")
        
    # Broadcast complete event
    await manager.broadcast({"type": "run_completed", "data": updated_run})
    return {"data": updated_run}

@app.get("/v1/runs", dependencies=[Depends(verify_api_key)])
async def list_runs(limit: int = 50, offset: int = 0, db = Depends(get_db)):
    runs = await get_runs(db, limit=limit, offset=offset)
    return {"data": runs}

@app.get("/v1/runs/{run_id}", dependencies=[Depends(verify_api_key)])
async def get_run(run_id: str, db = Depends(get_db)):
    run_details = await get_run_details(db, run_id=run_id)
    if not run_details:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"data": run_details}

# Spans Endpoints
@app.post("/v1/spans/batch", dependencies=[Depends(verify_api_key)])
@limiter.limit("1000/minute")
async def create_spans(request: Request, batch: SpanBatch, db = Depends(get_db)):
    span_dicts = [span.model_dump() for span in batch.spans]
    await insert_spans_batch(db, span_dicts)

    # Broadcast events for each span
    for span in span_dicts:
        await manager.broadcast({"type": "span_created", "data": span})

    return {"data": {"created": len(span_dicts), "failed": 0}}

# OTLP Protobuf Ingest
@app.post("/v1/traces", dependencies=[Depends(verify_api_key)])
async def ingest_otlp(request: Request, db = Depends(get_db)):
    body = await request.body()
    spans = decode_otlp_request(body)
    
    if spans:
        await insert_spans_batch(db, spans)
        # Broadcast all spans
        for span in spans:
            await manager.broadcast({"type": "span_created", "data": span})
            
    return {"data": {"spans_created": len(spans), "failed": 0}}

# WebSocket Connection with Authentication
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Verify API key during handshake
    if not await verify_websocket_api_key(websocket):
        await websocket.close(code=1008, reason="Unauthorized: Invalid or missing X-API-Key")
        return

    await manager.connect(websocket)
    try:
        while True:
            # Keep connection open, client messages are ignored in spike/MVP
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

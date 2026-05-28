from datetime import datetime
import json
import logging
from typing import List, Optional, Any, Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from db import (
    init_db, get_db, insert_run, insert_spans_batch, get_runs, get_run_details, update_run_status
)
from otlp import decode_otlp_request
from auth import verify_api_key

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agentwatch.main")

app = FastAPI(title="AgentWatch Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    await init_db()
    logger.info("Database initialized successfully.")

# Health Check
@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0", "time": datetime.now().isoformat()}

# Runs Endpoints
@app.post("/v1/runs", dependencies=[Depends(verify_api_key)])
async def create_run(run: RunCreate, db = Depends(get_db)):
    run_dict = run.dict()
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
async def create_spans(batch: SpanBatch, db = Depends(get_db)):
    span_dicts = [span.dict() for span in batch.spans]
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

# WebSocket Connection Gating (auth not applied to ws connection by default for simpler client hooks)
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection open, client messages are ignored in spike/MVP
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import os
from datetime import datetime
from db import init_db, get_db, insert_run, insert_span, get_runs, get_run_by_id
from otlp import decode_otlp_request
from auth import verify_api_key

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        dead = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                dead.append(connection)
        for conn in dead:
            self.active_connections.remove(conn)

manager = ConnectionManager()

# Models
class Run(BaseModel):
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

class Span(BaseModel):
    span_id: str
    run_id: str
    parent_span_id: Optional[str] = None
    span_type: str
    name: str
    model: Optional[str] = None
    provider: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    started_at: str
    ended_at: Optional[str] = None
    status: str = "running"
    error_message: Optional[str] = None
    metadata: dict = {}

class SpanBatch(BaseModel):
    spans: List[Span]

# Startup
@app.on_event("startup")
async def startup_event():
    await init_db()

# Health
@app.get("/health")
async def health():
    return {"status": "ok", "version": "spike-0.1"}

# Runs
@app.post("/v1/runs", dependencies=[Depends(verify_api_key)])
async def create_run(run: Run):
    db = await get_db()
    await insert_run(db, run.dict())
    await manager.broadcast({"type": "run_started", "data": run.dict()})
    return {"data": {"run_id": run.run_id, "status": "running"}}

@app.patch("/v1/runs/{run_id}", dependencies=[Depends(verify_api_key)])
async def update_run(run_id: str, update: RunUpdate):
    # Simplified: just broadcast, no actual update in spike
    await manager.broadcast({
        "type": "run_completed", 
        "data": {"run_id": run_id, "status": update.status}
    })
    return {"data": {"run_id": run_id, "status": update.status}}

@app.get("/v1/runs", dependencies=[Depends(verify_api_key)])
async def list_runs():
    db = await get_db()
    runs = await get_runs(db)
    return {"data": runs}

@app.get("/v1/runs/{run_id}", dependencies=[Depends(verify_api_key)])
async def get_run(run_id: str):
    db = await get_db()
    run = await get_run_by_id(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"data": run}

# Spans
@app.post("/v1/spans/batch", dependencies=[Depends(verify_api_key)])
async def create_spans(batch: SpanBatch):
    db = await get_db()
    for span in batch.spans:
        await insert_span(db, span.dict())
        await manager.broadcast({"type": "span_created", "data": span.dict()})
    return {"data": {"created": len(batch.spans), "failed": 0}}

# OTLP endpoint
@app.post("/v1/traces", dependencies=[Depends(verify_api_key)])
async def ingest_otlp(request: Request):
    body = await request.body()
    spans = decode_otlp_request(body)
    db = await get_db()
    for span_dict in spans:
        await insert_span(db, span_dict)
        await manager.broadcast({"type": "span_created", "data": span_dict})
    return {"data": {"spans_created": len(spans), "failed": 0}}

# WebSocket
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

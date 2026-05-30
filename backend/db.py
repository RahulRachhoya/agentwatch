import os
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Numeric, Text, Index
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID as PG_UUID
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import text

# Logging configuration
logger = logging.getLogger("agentwatch.db")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./aw.db")
if DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+asyncpg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
IS_POSTGRES = DATABASE_URL.startswith("postgresql")

# SQLAlchemy setup
connect_args = {"check_same_thread": False} if not IS_POSTGRES else {}

engine_args = {
    "echo": False,
    "connect_args": connect_args
}

if IS_POSTGRES:
    engine_args["pool_size"] = 20
    engine_args["max_overflow"] = 10
    engine_args["pool_pre_ping"] = True

engine = create_async_engine(
    DATABASE_URL,
    **engine_args
)

async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

# Declare dynamic JSON type mapping
JSON_TYPE = JSONB if IS_POSTGRES else Text

class Run(Base):
    __tablename__ = "runs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    session_id = Column(String, index=True, nullable=True)
    
    # In SQLite, ARRAY is not natively supported, so we serialize tags as JSON or fallback to TEXT.
    # In Postgres, we use native ARRAY(Text).
    tags = Column(ARRAY(String) if IS_POSTGRES else Text, default=[] if IS_POSTGRES else "[]")
    
    started_at = Column(DateTime(timezone=True), nullable=False, index=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    
    status = Column(String, nullable=False, default="running", index=True)
    error_message = Column(Text, nullable=True)
    
    total_tokens = Column(Integer, default=0)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_cost_usd = Column(Numeric(10, 6), default=0.0)
    span_count = Column(Integer, default=0)
    tool_call_count = Column(Integer, default=0)
    
    metadata_ = Column("metadata", JSON_TYPE, default="{}" if not IS_POSTGRES else {})
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Span(Base):
    __tablename__ = "spans"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    span_id = Column(String, unique=True, nullable=False, index=True)
    run_id = Column(String, nullable=False, index=True)
    parent_span_id = Column(String, nullable=True)
    
    span_type = Column(String, nullable=False, index=True)  # llm | tool | chain | retriever | custom
    name = Column(String, nullable=False)
    
    model = Column(String, nullable=True, index=True)
    provider = Column(String, nullable=True)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost_usd = Column(Numeric(10, 6), default=0.0)
    
    input_preview = Column(Text, nullable=True)
    output_preview = Column(Text, nullable=True)
    
    started_at = Column(DateTime(timezone=True), nullable=False, index=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    
    status = Column(String, nullable=False, default="running")
    error_type = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    
    tool_name = Column(String, nullable=True)
    tool_input = Column(JSON_TYPE, nullable=True)
    tool_output = Column(JSON_TYPE, nullable=True)
    
    metadata_ = Column("metadata", JSON_TYPE, default="{}" if not IS_POSTGRES else {})
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class ModelPricing(Base):
    __tablename__ = "model_pricing"
    
    model = Column(String, primary_key=True)
    provider = Column(String, nullable=False)
    input_cost_per_1k_tokens = Column(Numeric(8, 6), nullable=False)
    output_cost_per_1k_tokens = Column(Numeric(8, 6), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class MetricHourly(Base):
    __tablename__ = "metrics_hourly"
    
    hour = Column(DateTime(timezone=True), primary_key=True)
    run_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    total_cost_usd = Column(Numeric(12, 4), default=0.0)
    avg_duration_ms = Column(Integer, nullable=True)
    p95_duration_ms = Column(Integer, nullable=True)

# Helper function to helper serialize JSON metadata appropriately
def _to_json(val: Any) -> Any:
    if IS_POSTGRES:
        return val if isinstance(val, (dict, list)) else {}
    return json.dumps(val) if isinstance(val, (dict, list)) else "{}"

# DB Initialization
async def init_db():
    async with engine.begin() as conn:
        # Create all tables natively
        await conn.run_sync(Base.metadata.create_all)
        
        # Seed model pricing on startup
        await seed_pricing(conn)

async def seed_pricing(conn):
    # Check if we have pricing records, if not seed them
    # Extended v2 model list (including DeepSeek, Kimi, Bedrock models)
    pricing_data = [
        # OpenAI
        {"model": "gpt-4o", "provider": "openai", "input_cost_per_1k_tokens": 0.005, "output_cost_per_1k_tokens": 0.015},
        {"model": "gpt-4o-mini", "provider": "openai", "input_cost_per_1k_tokens": 0.00015, "output_cost_per_1k_tokens": 0.0006},
        {"model": "gpt-4-turbo", "provider": "openai", "input_cost_per_1k_tokens": 0.01, "output_cost_per_1k_tokens": 0.03},
        {"model": "gpt-3.5-turbo", "provider": "openai", "input_cost_per_1k_tokens": 0.0005, "output_cost_per_1k_tokens": 0.0015},
        # Anthropic
        {"model": "claude-3-5-sonnet", "provider": "anthropic", "input_cost_per_1k_tokens": 0.003, "output_cost_per_1k_tokens": 0.015},
        {"model": "claude-3-haiku", "provider": "anthropic", "input_cost_per_1k_tokens": 0.00025, "output_cost_per_1k_tokens": 0.00125},
        {"model": "claude-3-opus", "provider": "anthropic", "input_cost_per_1k_tokens": 0.015, "output_cost_per_1k_tokens": 0.075},
        # Google
        {"model": "gemini-1.5-pro", "provider": "google", "input_cost_per_1k_tokens": 0.00125, "output_cost_per_1k_tokens": 0.005},
        {"model": "gemini-1.5-flash", "provider": "google", "input_cost_per_1k_tokens": 0.000075, "output_cost_per_1k_tokens": 0.0003},
        # Mistral
        {"model": "mistral-7b", "provider": "mistral", "input_cost_per_1k_tokens": 0.00025, "output_cost_per_1k_tokens": 0.00025},
        {"model": "mixtral-8x7b", "provider": "mistral", "input_cost_per_1k_tokens": 0.0007, "output_cost_per_1k_tokens": 0.0007},
        # DeepSeek
        {"model": "deepseek-chat", "provider": "deepseek", "input_cost_per_1k_tokens": 0.00014, "output_cost_per_1k_tokens": 0.00028},
        {"model": "deepseek-reasoner", "provider": "deepseek", "input_cost_per_1k_tokens": 0.00055, "output_cost_per_1k_tokens": 0.0022},
        # Moonshot / Kimi
        {"model": "moonshot-v1-8k", "provider": "moonshot", "input_cost_per_1k_tokens": 0.00012, "output_cost_per_1k_tokens": 0.00012},
        {"model": "moonshot-v1-32k", "provider": "moonshot", "input_cost_per_1k_tokens": 0.00024, "output_cost_per_1k_tokens": 0.00024},
        {"model": "moonshot-v1-128k", "provider": "moonshot", "input_cost_per_1k_tokens": 0.00060, "output_cost_per_1k_tokens": 0.00060},
        # AWS Bedrock model IDs
        {"model": "anthropic.claude-3-5-sonnet-20241022-v2:0", "provider": "bedrock", "input_cost_per_1k_tokens": 0.003, "output_cost_per_1k_tokens": 0.015},
        {"model": "anthropic.claude-3-haiku-20240307-v1:0", "provider": "bedrock", "input_cost_per_1k_tokens": 0.00025, "output_cost_per_1k_tokens": 0.00125},
        {"model": "meta.llama3-1-70b-instruct-v1:0", "provider": "bedrock", "input_cost_per_1k_tokens": 0.00099, "output_cost_per_1k_tokens": 0.00099},
        {"model": "meta.llama3-1-8b-instruct-v1:0", "provider": "bedrock", "input_cost_per_1k_tokens": 0.0003, "output_cost_per_1k_tokens": 0.0003},
        {"model": "amazon.titan-text-express-v1", "provider": "bedrock", "input_cost_per_1k_tokens": 0.0002, "output_cost_per_1k_tokens": 0.0006},
        {"model": "cohere.command-r-plus-v1:0", "provider": "bedrock", "input_cost_per_1k_tokens": 0.003, "output_cost_per_1k_tokens": 0.015},
        {"model": "mistral.mistral-large-2402-v1:0", "provider": "bedrock", "input_cost_per_1k_tokens": 0.008, "output_cost_per_1k_tokens": 0.024}
    ]
    
    # We construct raw SQL insert or update for portability
    for item in pricing_data:
        # ON CONFLICT support
        if IS_POSTGRES:
            query = text("""
                INSERT INTO model_pricing (model, provider, input_cost_per_1k_tokens, output_cost_per_1k_tokens, updated_at)
                VALUES (:model, :provider, :input_cost_per_1k_tokens, :output_cost_per_1k_tokens, NOW())
                ON CONFLICT (model) DO UPDATE SET
                    input_cost_per_1k_tokens = EXCLUDED.input_cost_per_1k_tokens,
                    output_cost_per_1k_tokens = EXCLUDED.output_cost_per_1k_tokens,
                    updated_at = NOW()
            """)
        else:
            query = text("""
                INSERT INTO model_pricing (model, provider, input_cost_per_1k_tokens, output_cost_per_1k_tokens, updated_at)
                VALUES (:model, :provider, :input_cost_per_1k_tokens, :output_cost_per_1k_tokens, datetime('now'))
                ON CONFLICT (model) DO UPDATE SET
                    input_cost_per_1k_tokens = EXCLUDED.input_cost_per_1k_tokens,
                    output_cost_per_1k_tokens = EXCLUDED.output_cost_per_1k_tokens,
                    updated_at = datetime('now')
            """)
        await conn.execute(query, item)

# Session generator
async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session

# Helper to parse datetime strings or leave datetimes as is
def parse_dt(dt_val: Any) -> Optional[datetime]:
    if not dt_val:
        return None
    if isinstance(dt_val, datetime):
        return dt_val
    try:
        # Handles typical ISO format (e.g. 2026-05-28T17:08:48.000Z or similar)
        # Replacing 'Z' with '+00:00' to support python ISO parsing
        if dt_val.endswith("Z"):
            dt_val = dt_val[:-1] + "+00:00"
        return datetime.fromisoformat(dt_val)
    except Exception as e:
        logger.warning(f"Failed to parse datetime '{dt_val}': {e}")
        return datetime.now(timezone.utc)

# Operations
async def insert_run(db: AsyncSession, run_dict: Dict[str, Any]):
    """Insert or update a run."""
    started_at = parse_dt(run_dict["started_at"])
    ended_at = parse_dt(run_dict.get("ended_at"))
    
    duration_ms = None
    if started_at and ended_at:
        duration_ms = int((ended_at - started_at).total_seconds() * 1000)
    elif run_dict.get("duration_ms"):
        duration_ms = int(run_dict["duration_ms"])
        
    tags_data = run_dict.get("tags", [])
    if not isinstance(tags_data, list):
        tags_data = [tags_data] if tags_data else []
    if not IS_POSTGRES:
        tags_data = json.dumps(tags_data)

    query = text("""
        INSERT INTO runs (
            run_id, name, session_id, tags, started_at, ended_at, 
            duration_ms, status, error_message, metadata, created_at
        ) VALUES (
            :run_id, :name, :session_id, :tags, :started_at, :ended_at,
            :duration_ms, :status, :error_message, :metadata, :created_at
        )
        ON CONFLICT (run_id) DO UPDATE SET
            ended_at = EXCLUDED.ended_at,
            duration_ms = COALESCE(EXCLUDED.duration_ms, runs.duration_ms),
            status = EXCLUDED.status,
            error_message = EXCLUDED.error_message,
            metadata = EXCLUDED.metadata
    """)
    
    await db.execute(query, {
        "run_id": run_dict["run_id"],
        "name": run_dict["name"],
        "session_id": run_dict.get("session_id"),
        "tags": tags_data,
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_ms": duration_ms,
        "status": run_dict.get("status", "running"),
        "error_message": run_dict.get("error_message"),
        "metadata": _to_json(run_dict.get("metadata", {})),
        "created_at": datetime.now(timezone.utc)
    })
    await db.commit()

async def insert_spans_batch(db: AsyncSession, span_dicts: List[Dict[str, Any]]):
    """Insert a batch of spans in a single transaction with conflict resolution."""
    if not span_dicts:
        return
        
    # We resolve pricing to compute cost_usd for each span on the server side
    # Fetch pricing mapping
    pricing_result = await db.execute(text("SELECT model, input_cost_per_1k_tokens, output_cost_per_1k_tokens FROM model_pricing"))
    pricing = {row[0]: (float(row[1]), float(row[2])) for row in pricing_result.fetchall()}

    params = []
    for span_dict in span_dicts:
        started_at = parse_dt(span_dict["started_at"])
        ended_at = parse_dt(span_dict.get("ended_at"))
        
        duration_ms = None
        if started_at and ended_at:
            duration_ms = int((ended_at - started_at).total_seconds() * 1000)
        elif span_dict.get("duration_ms"):
            duration_ms = int(span_dict["duration_ms"])
            
        # Calculate cost
        cost_usd = 0.0
        model = span_dict.get("model")
        prompt_tokens = span_dict.get("prompt_tokens", 0) or 0
        completion_tokens = span_dict.get("completion_tokens", 0) or 0
        total_tokens = prompt_tokens + completion_tokens
        
        if model and model in pricing:
            in_cost, out_cost = pricing[model]
            cost_usd = (prompt_tokens * in_cost / 1000.0) + (completion_tokens * out_cost / 1000.0)
        
        params.append({
            "span_id": span_dict["span_id"],
            "run_id": span_dict["run_id"],
            "parent_span_id": span_dict.get("parent_span_id"),
            "span_type": span_dict["span_type"],
            "name": span_dict["name"],
            "model": model,
            "provider": span_dict.get("provider"),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost_usd": cost_usd,
            "input_preview": span_dict.get("input_preview"),
            "output_preview": span_dict.get("output_preview"),
            "started_at": started_at,
            "ended_at": ended_at,
            "duration_ms": duration_ms,
            "status": span_dict.get("status", "running"),
            "error_type": span_dict.get("error_type"),
            "error_message": span_dict.get("error_message"),
            "tool_name": span_dict.get("tool_name"),
            "tool_input": _to_json(span_dict.get("tool_input")),
            "tool_output": _to_json(span_dict.get("tool_output")),
            "metadata": _to_json(span_dict.get("metadata", {})),
            "created_at": datetime.now(timezone.utc)
        })

    query = text("""
        INSERT INTO spans (
            span_id, run_id, parent_span_id, span_type, name, 
            model, provider, prompt_tokens, completion_tokens, total_tokens, cost_usd,
            input_preview, output_preview, started_at, ended_at, duration_ms,
            status, error_type, error_message, tool_name, tool_input, tool_output,
            metadata, created_at
        ) VALUES (
            :span_id, :run_id, :parent_span_id, :span_type, :name,
            :model, :provider, :prompt_tokens, :completion_tokens, :total_tokens, :cost_usd,
            :input_preview, :output_preview, :started_at, :ended_at, :duration_ms,
            :status, :error_type, :error_message, :tool_name, :tool_input, :tool_output,
            :metadata, :created_at
        )
        ON CONFLICT (span_id) DO UPDATE SET
            ended_at = CASE 
                WHEN spans.status IN ('success', 'error') THEN spans.ended_at 
                ELSE EXCLUDED.ended_at 
            END,
            duration_ms = CASE 
                WHEN spans.status IN ('success', 'error') THEN spans.duration_ms 
                ELSE COALESCE(EXCLUDED.duration_ms, spans.duration_ms) 
            END,
            status = CASE 
                WHEN spans.status IN ('success', 'error') THEN spans.status 
                ELSE EXCLUDED.status 
            END,
            error_type = CASE 
                WHEN spans.status IN ('success', 'error') THEN spans.error_type 
                ELSE EXCLUDED.error_type 
            END,
            error_message = CASE 
                WHEN spans.status IN ('success', 'error') THEN spans.error_message 
                ELSE EXCLUDED.error_message 
            END,
            tool_output = CASE 
                WHEN spans.status IN ('success', 'error') THEN spans.tool_output 
                ELSE EXCLUDED.tool_output 
            END,
            prompt_tokens = CASE 
                WHEN spans.status IN ('success', 'error') THEN spans.prompt_tokens 
                ELSE EXCLUDED.prompt_tokens 
            END,
            completion_tokens = CASE 
                WHEN spans.status IN ('success', 'error') THEN spans.completion_tokens 
                ELSE EXCLUDED.completion_tokens 
            END,
            total_tokens = CASE 
                WHEN spans.status IN ('success', 'error') THEN spans.total_tokens 
                ELSE EXCLUDED.total_tokens 
            END,
            cost_usd = CASE 
                WHEN spans.status IN ('success', 'error') THEN spans.cost_usd 
                ELSE EXCLUDED.cost_usd 
            END,
            metadata = EXCLUDED.metadata
    """)
    
    # Execute batch inserts
    await db.execute(query, params)
    await db.commit()
    
    # Trigger denormalized aggregations update on affected runs
    run_ids = list(set(s["run_id"] for s in span_dicts))
    await update_run_aggregates(db, run_ids)

async def update_run_aggregates(db: AsyncSession, run_ids: List[str]):
    """Denormalize metrics from spans into the runs table for fast dashboard queries."""
    if not run_ids:
        return
        
    for run_id in run_ids:
        # Aggregation query
        agg_result = await db.execute(text("""
            SELECT 
                COUNT(id) as span_count,
                SUM(prompt_tokens) as prompt_tokens,
                SUM(completion_tokens) as completion_tokens,
                SUM(total_tokens) as total_tokens,
                SUM(cost_usd) as total_cost_usd,
                COUNT(CASE WHEN span_type = 'tool' THEN 1 END) as tool_call_count
            FROM spans
            WHERE run_id = :run_id
        """), {"run_id": run_id})
        
        row = agg_result.fetchone()
        if not row or row[0] == 0:
            continue
            
        span_count, prompt_t, comp_t, total_t, cost, tool_count = row
        
        await db.execute(text("""
            UPDATE runs SET
                span_count = :span_count,
                prompt_tokens = :prompt_tokens,
                completion_tokens = :completion_tokens,
                total_tokens = :total_tokens,
                total_cost_usd = :total_cost_usd,
                tool_call_count = :tool_call_count
            WHERE run_id = :run_id
        """), {
            "run_id": run_id,
            "span_count": span_count,
            "prompt_tokens": prompt_t or 0,
            "completion_tokens": comp_t or 0,
            "total_tokens": total_t or 0,
            "total_cost_usd": cost or 0.0,
            "tool_call_count": tool_count or 0
        })
    await db.commit()

async def get_runs(db: AsyncSession, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """Retrieve runs list with pagination."""
    result = await db.execute(text("""
        SELECT * FROM runs 
        ORDER BY started_at DESC 
        LIMIT :limit OFFSET :offset
    """), {"limit": limit, "offset": offset})
    rows = result.fetchall()
    return [dict(row._mapping) for row in rows]

async def get_run_details(db: AsyncSession, run_id: str) -> Optional[Dict[str, Any]]:
    """Get all details of a run, including its hierarchical spans."""
    run_result = await db.execute(text("SELECT * FROM runs WHERE run_id = :run_id"), {"run_id": run_id})
    run_row = run_result.fetchone()
    if not run_row:
        return None
        
    spans_result = await db.execute(text("SELECT * FROM spans WHERE run_id = :run_id ORDER BY started_at ASC"), {"run_id": run_id})
    spans_rows = spans_result.fetchall()
    
    run_dict = dict(run_row._mapping)
    run_dict["spans"] = [dict(span._mapping) for span in spans_rows]
    return run_dict

async def update_run_status(db: AsyncSession, run_id: str, status: str, ended_at: Optional[Any], error_message: Optional[str]) -> Optional[Dict[str, Any]]:
    """Update status, ended_at, and duration of an existing run."""
    parsed_ended = parse_dt(ended_at)
    
    # Fetch started_at to compute duration
    run_result = await db.execute(text("SELECT started_at FROM runs WHERE run_id = :run_id"), {"run_id": run_id})
    row = run_result.fetchone()
    if not row:
        return None
        
    started_at = parse_dt(row[0])
    duration_ms = None
    if started_at and parsed_ended:
        # Support both offset-naive and offset-aware comparisons
        if started_at.tzinfo is None and parsed_ended.tzinfo is not None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        elif started_at.tzinfo is not None and parsed_ended.tzinfo is None:
            parsed_ended = parsed_ended.replace(tzinfo=timezone.utc)
        duration_ms = int((parsed_ended - started_at).total_seconds() * 1000)

    await db.execute(text("""
        UPDATE runs SET
            status = :status,
            ended_at = :ended_at,
            duration_ms = COALESCE(:duration_ms, duration_ms),
            error_message = :error_message
        WHERE run_id = :run_id
    """), {
        "run_id": run_id,
        "status": status,
        "ended_at": parsed_ended,
        "duration_ms": duration_ms,
        "error_message": error_message
    })
    await db.commit()
    
    # Retrieve updated run record
    updated = await db.execute(text("SELECT * FROM runs WHERE run_id = :run_id"), {"run_id": run_id})
    updated_row = updated.fetchone()
    return dict(updated_row._mapping) if updated_row else None


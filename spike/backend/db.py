import os
import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./aw.db")

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        # Detect dialect
        dialect = engine.dialect.name
        json_type = "JSONB" if dialect == "postgresql" else "JSON"
        
        await conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS runs (
            id SERIAL PRIMARY KEY,
            run_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            session_id TEXT,
            tags TEXT,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            status TEXT DEFAULT 'running',
            error_message TEXT,
            metadata {json_type}
        )
        """))
        
        await conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS spans (
            id SERIAL PRIMARY KEY,
            span_id TEXT UNIQUE NOT NULL,
            run_id TEXT NOT NULL,
            parent_span_id TEXT,
            span_type TEXT NOT NULL,
            name TEXT NOT NULL,
            model TEXT,
            provider TEXT,
            prompt_tokens INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            status TEXT DEFAULT 'running',
            error_message TEXT,
            metadata {json_type}
        )
        """))

async def get_db():
    async with async_session() as session:
        return session

async def insert_run(db, run_dict):
    await db.execute(text("""
        INSERT INTO runs (run_id, name, session_id, tags, started_at, metadata)
        VALUES (:run_id, :name, :session_id, :tags, :started_at, :metadata)
        ON CONFLICT (run_id) DO NOTHING
    """), {
        "run_id": run_dict["run_id"],
        "name": run_dict["name"],
        "session_id": run_dict.get("session_id"),
        "tags": str(run_dict.get("tags", [])),
        "started_at": run_dict["started_at"],
        "metadata": json.dumps(run_dict.get("metadata", {}))
    })
    await db.commit()

async def insert_span(db, span_dict):
    await db.execute(text("""
        INSERT INTO spans (
            span_id, run_id, parent_span_id, span_type, name, 
            model, provider, prompt_tokens, completion_tokens,
            started_at, ended_at, status, error_message, metadata
        ) VALUES (
            :span_id, :run_id, :parent_span_id, :span_type, :name,
            :model, :provider, :prompt_tokens, :completion_tokens,
            :started_at, :ended_at, :status, :error_message, :metadata
        )
        ON CONFLICT (span_id) DO UPDATE SET
            ended_at = EXCLUDED.ended_at,
            status = EXCLUDED.status,
            metadata = EXCLUDED.metadata
    """), {
        "span_id": span_dict["span_id"],
        "run_id": span_dict["run_id"],
        "parent_span_id": span_dict.get("parent_span_id"),
        "span_type": span_dict["span_type"],
        "name": span_dict["name"],
        "model": span_dict.get("model"),
        "provider": span_dict.get("provider"),
        "prompt_tokens": span_dict.get("prompt_tokens", 0),
        "completion_tokens": span_dict.get("completion_tokens", 0),
        "started_at": span_dict["started_at"],
        "ended_at": span_dict.get("ended_at"),
        "status": span_dict.get("status", "running"),
        "error_message": span_dict.get("error_message"),
        "metadata": json.dumps(span_dict.get("metadata", {}))
    })
    await db.commit()

async def get_runs(db):
    result = await db.execute(text("SELECT * FROM runs ORDER BY started_at DESC LIMIT 20"))
    rows = result.fetchall()
    return [dict(row._mapping) for row in rows]

async def get_run_by_id(db, run_id):
    result = await db.execute(text("SELECT * FROM runs WHERE run_id = :run_id"), {"run_id": run_id})
    row = result.fetchone()
    return dict(row._mapping) if row else None

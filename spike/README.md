# AgentWatch Phase 0 Spike

Throwaway validation code for AgentWatch architecture assumptions. Tests FastAPI + Postgres/SQLite ingest, SDK patches, OTLP compatibility before Phase 1 MVP build.

## Structure

```
spike/
├── backend/           # FastAPI server (dual Postgres/SQLite)
│   ├── main.py       # Routes: /v1/runs, /v1/spans/batch, /v1/traces, /ws, /health
│   ├── db.py         # SQLAlchemy async with dual driver support
│   ├── otlp.py       # OTLP protobuf decoder
│   └── auth.py       # X-API-Key middleware
├── frontend/         # WebSocket test client (vanilla JS)
│   └── index.html
├── tests/
│   ├── load/         # Performance tests
│   │   └── ingest_load.py
│   └── integration/  # SDK patches + integration tests
│       ├── patch_openai.py
│       ├── patch_anthropic.py
│       ├── patch_bedrock.py
│       ├── patch_openai_compat.py  # DeepSeek, Kimi
│       ├── langchain_callback.py
│       └── otel_emitter.py
├── docs/             # Documentation + results
│   ├── README.md     # Spike questions (Q1-Q9)
│   └── SPIKE_RESULTS.md
├── evidence/         # Validation evidence (gitignored)
│   └── Q{n}/
└── docker-compose.yml
```

## Quick Start

```bash
# Start backend + postgres
docker-compose up -d

# Run load test (Q1/Q2)
python tests/load/ingest_load.py --dsn postgres

# Test SDK patches (Q4/Q5)
cd tests/integration
OPENAI_API_KEY=xxx python patch_openai.py

# Test OTLP (Q6)
python tests/integration/otel_emitter.py
```

## Validation Status

| Q | Test | Status | Evidence |
|---|------|--------|----------|
| Q8 | docker-compose clean start | ✅ PASS | evidence/Q8/ |
| Q1 | Postgres 100 spans/sec | ❌ FAIL | Needs connection pooling |
| Q4 | OpenAI patch sync/async/stream | ✅ PASS | evidence/Q4/ |
| Q5 | Multi-provider patches | ✅ PASS | evidence/Q5/ |
| Q6 | OTLP protobuf ingest | ✅ PASS | evidence/Q6/ |
| Q2 | SQLite perf | ⏳ PENDING | - |
| Q3 | LangChain tokens | ⏳ PENDING | - |
| Q7 | WebSocket delivery | ⏳ PENDING | - |
| Q9 | API key auth toggle | ⏳ PENDING | - |

See `docs/SPIKE_RESULTS.md` for full results.

## Issues Found

1. **Schema mismatch**: Load test used `start_time`/`end_time` (float), backend expected `started_at`/`ended_at` (str) → Fixed
2. **JSON serialization**: `db.py` used `str(metadata)` instead of `json.dumps()` → Fixed
3. **Bedrock body reread**: Lambda couldn't reread response body → Fixed with `RereadableBody` class
4. **Q1 perf**: No connection pooling, per-span commits → Phase 1 fix

## Phase 1 Recommendations

- Add asyncpg connection pool (10-20 connections)
- Batch span inserts (commit every 50-100)
- Remove SQLAlchemy `echo=True`
- Test on Linux (Docker Desktop Windows unstable)

---

**Note:** This code is throwaway. Phase 1 MVP rebuilds from scratch using spike learnings.

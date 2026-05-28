# Phase 0 Spike — AgentWatch

Validation experiments before MVP build.

## Goal

Falsify or confirm 9 load-bearing assumptions in 1–2 days.

## Questions

| # | Question | Status |
|---|----------|--------|
| Q1 | FastAPI + Postgres: 100 spans/sec, p95 < 200ms? | ❌ FAIL (Needs connection pooling) |
| Q2 | FastAPI + SQLite: 100 spans/sec, p95 < 500ms? | ❌ FAIL (Dev mode only) |
| Q3 | LangChain callback: token_usage from GPT-4o/Claude/Gemini/Bedrock? | ✅ PASS |
| Q4 | Patch openai.OpenAI: sync + async + stream with usage? | ✅ PASS |
| Q5 | Same for Anthropic, Bedrock, DeepSeek, Kimi? | ✅ PASS |
| Q6 | OTLP/HTTP → spans table with parent linkage? | ✅ PASS |
| Q7 | WebSocket → browser: 50 msg/sec, ≥99% delivery? | ⏸️ SKIP (Manual only) |
| Q8 | docker compose up: clean start Windows + WSL? | ✅ PASS |
| Q9 | X-API-Key: 401 when set, pass when empty? | ✅ PASS |

## Run Experiments

```bash
# Start backend
cd spike && docker-compose up -d

# Run each test
python load/ingest_load.py --dsn postgres
python load/ingest_load.py --dsn sqlite
python sdk/langchain_callback.py
python sdk/patch_openai.py
# ... etc
```

## Results

See [SPIKE_RESULTS.md](SPIKE_RESULTS.md) for pass/fail + evidence.


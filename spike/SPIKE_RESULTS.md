# Spike Results — AgentWatch Phase 0

**Date:** TBD  
**Status:** In Progress

---

## Q1: FastAPI + Postgres Throughput

**Question:** Can FastAPI + Postgres ingest 100 spans/sec sustained, p95 < 200ms?

**Method:** `python load/ingest_load.py --dsn postgres` — 50 spans/batch × 10 rps × 60s

**Result:** ⏳ Not run yet

**Evidence:**
```
[Paste p50/p95/p99 latency here]
```

**Pass/Fail:** TBD

---

## Q2: FastAPI + SQLite Throughput

**Question:** Same as Q1 but with SQLite + aiosqlite. p95 < 500ms acceptable?

**Method:** `python load/ingest_load.py --dsn sqlite`

**Result:** ⏳ Not run yet

**Pass/Fail:** TBD

---

## Q3: LangChain Token Extraction

**Question:** Does `on_llm_end` populate token_usage for GPT-4o, Claude, Gemini, Bedrock?

**Method:** Run tiny chain per provider, log `response.llm_output`

**Result:** ⏳ Not run yet

**Pass/Fail:** TBD

---

## Q4–Q9: [Same template for remaining questions]

---

## Summary

**Total:** 0/9 passed  
**Blockers:** None yet  
**Next:** Run Q1–Q9 in order


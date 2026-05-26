# PRD: AgentWatch — Open-Source LLM Agent Monitoring Dashboard

**Author:** Rahul Rachhoya  
**Status:** Draft  
**Version:** 2.0  
**Date:** May 26, 2026  
**Type:** Greenfield OSS Project  

**Changes from v1.0:**
- Added Phase 0 spike validation requirements (§10.0)
- Promoted OTel compat, SQLite dev mode, API auth from v1.1 → v1.0 scope (§7.1, §7.3)
- Added native multi-provider SDK patches (OpenAI, Anthropic, Bedrock, DeepSeek, Kimi) (§7.4.3)
- Expanded model_pricing seed data for new providers (§7.2.4)
- 10 MVP design adjustments from spike findings (§13.1)
- Updated technical stack with dual DB support (§8)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Background & Why Now](#2-background--why-now)
3. [Problem Statement](#3-problem-statement)
4. [Goals & Non-Goals](#4-goals--non-goals)
5. [Target Users & Market Segments](#5-target-users--market-segments)
6. [Value Proposition & Competitive Analysis](#6-value-proposition--competitive-analysis)
7. [Solution — Full Feature Specification](#7-solution--full-feature-specification)
8. [Technical Stack Decision](#8-technical-stack-decision)
9. [User Flows](#9-user-flows)
10. [Release Plan — Phase by Phase](#10-release-plan--phase-by-phase)
11. [Ticket Breakdown](#11-ticket-breakdown-github-issues)
12. [Success Metrics](#12-success-metrics)
13. [Risks & Design Adjustments](#13-risks--design-adjustments)
14. [Open Questions](#14-open-questions)
15. [Appendix](#15-appendix--competitor-deep-dive)

---

## 1. Executive Summary

**AgentWatch** is a self-hostable, open-source LLM agent monitoring dashboard. Real-time visibility into agent runs — cost, tokens, latency per step, tool calls, error traces — across any framework (LangGraph, CrewAI, AutoGen, raw APIs).

**Core hook:** LangSmith costs $39/month/seat. AgentWatch is free. One `docker-compose up` + 3-line Python SDK. Zero data leaves infrastructure.

**v2 differentiators vs v1 plan:**
- **OpenTelemetry compatibility** — accepts OTLP traces alongside native `/v1/spans`. Existing OTel users zero-code integration.
- **SQLite dev mode** — `DATABASE_URL=sqlite:///aw.db` for local dev without Postgres container.
- **Multi-provider native patches** — auto-instrument OpenAI, Anthropic, Bedrock, DeepSeek, Kimi without LangChain dependency.
- **Optional API-key auth** — `X-API-Key` header on ingest prevents network spam in shared envs.

---

## 2–6. [Unchanged from v1.0]

Sections 2 (Background), 3 (Problem), 4 (Goals), 5 (Users), 6 (Competition) remain identical to v1.0. See `PRD-AgentWatch.md` §2-6 for full text.

**Key v1.0 goals restated:**
- G1: Any Python dev monitoring in <5 min
- G2: Track cost/latency/tokens/tools out of box
- G3: Real-time dashboard (no refresh)
- G4: LangChain, LangGraph, CrewAI, raw API support
- G5: `docker-compose up` — zero cloud deps
- G6: 50+ GitHub stars in 30 days
- G7: Live public demo for portfolio

---

## 7. Solution — Full Feature Specification

### 7.1 System Architecture (Updated)

```
┌─────────────────────────────────────────────────────────────┐
│                     Your Python App                         │
│                                                             │
│  # Option 1: LangChain callback                             │
│  import agentwatch                                          │
│  aw = agentwatch.init("http://localhost:8000")              │
│  chain = agent.with_config(callbacks=[aw.callback_handler]) │
│                                                             │
│  # Option 2: Native patch (no LangChain)                    │
│  aw.patch_openai(openai_client)                             │
│  aw.patch_anthropic(anthropic_client)                       │
│                                                             │
│  # Option 3: Existing OTel instrumentation                  │
│  # Point OTLP exporter → http://localhost:8000/v1/traces    │
│                                     │                       │
└─────────────────────────────────────┼───────────────────────┘
                                      │ HTTP POST /v1/spans
                                      │ HTTP POST /v1/traces (OTLP)
                                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  AgentWatch Backend (FastAPI)                │
│                                                             │
│  ┌──────────────┐  ┌────────────────┐  ┌─────────────────┐ │
│  │  Ingest API  │  │  Query API     │  │  WebSocket Hub  │ │
│  │  /v1/spans   │  │  /v1/runs      │  │  /ws            │ │
│  │  /v1/traces  │  │  /v1/metrics   │  │                 │ │
│  │  (OTLP)      │  │                │  │                 │ │
│  └──────┬───────┘  └───────┬────────┘  └────────┬────────┘ │
│         │                  │                     │          │
│         │       Optional: X-API-Key middleware   │          │
│         ▼                  ▼                     ▼          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │   PostgreSQL (prod) OR SQLite (dev) + pgvector      │   │
│  │   tables: runs, spans, metrics_hourly, model_pricing│   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────┐
│                 AgentWatch Frontend (React/TS)               │
│                                                             │
│  / Dashboard → Live Runs + Cost + Latency charts           │
│  /runs       → Filterable run list                          │
│  /runs/:id   → Span waterfall + metrics + raw JSON         │
│  /metrics    → Cost/latency/error analytics                 │
│  /settings   → Model pricing, retention, OTel toggle        │
└─────────────────────────────────────────────────────────────┘
```

**v2 changes:**
- Added `/v1/traces` OTLP endpoint
- Dual DB support (Postgres prod / SQLite dev)
- Native SDK patches (no LangChain requirement)
- Optional `X-API-Key` auth middleware

---

### 7.2 Data Model & Schema

#### 7.2.1–7.2.3 Tables: runs, spans, metrics_hourly

**[Unchanged from v1.0 §7.2]** — see original PRD for full `CREATE TABLE` statements.

**v2 adjustment:** `spans.metadata JSONB` may contain:
- `source: 'otel'` — span ingested via OTLP endpoint
- `otel.trace_id` — original OTel trace ID (before mapping to `run_id`)

---

#### 7.2.4 Table: model_pricing (Extended Seed Data)

**v1.0 seed covered:** GPT-4o, Claude 3.5, Gemini, Mistral.

**v2.0 adds:**

```sql
-- DeepSeek
('deepseek-chat',                'deepseek',   0.00014,  0.00028),
('deepseek-reasoner',            'deepseek',   0.00055,  0.0022),

-- Kimi (Moonshot)
('moonshot-v1-8k',               'moonshot',   0.00012,  0.00012),
('moonshot-v1-32k',              'moonshot',   0.00024,  0.00024),
('moonshot-v1-128k',             'moonshot',   0.00060,  0.00060),

-- AWS Bedrock model IDs (per-model token pricing)
('anthropic.claude-3-5-sonnet-20241022-v2:0',  'bedrock', 0.003,  0.015),
('anthropic.claude-3-haiku-20240307-v1:0',     'bedrock', 0.00025,0.00125),
('meta.llama3-1-70b-instruct-v1:0',            'bedrock', 0.00099,0.00099),
('meta.llama3-1-8b-instruct-v1:0',             'bedrock', 0.0003, 0.0003),
('amazon.titan-text-express-v1',               'bedrock', 0.0002, 0.0006),
('cohere.command-r-plus-v1:0',                 'bedrock', 0.003,  0.015),
('mistral.mistral-large-2402-v1:0',            'bedrock', 0.008,  0.024);
```

**Why:** Phase 0 spike validates Bedrock + DeepSeek + Kimi. MVP must ship with their pricing or cost calculation breaks.

---

### 7.3 API Design (All Endpoints)

**v1.0 endpoints remain:** `POST /v1/runs`, `PATCH /v1/runs/:id`, `POST /v1/spans/batch`, `GET /v1/runs`, `GET /v1/runs/:id`, `GET /v1/metrics/*`, `GET /health`.

#### 7.3.1 NEW: POST `/v1/traces` — OTLP Ingest

Accepts OpenTelemetry protobuf traces.

```
POST /v1/traces
Content-Type: application/x-protobuf
Body: ExportTraceServiceRequest (protobuf)

Response 200:
{
  "data": {
    "spans_created": 3,
    "failed": 0
  }
}
```

**Mapping rules:**
- `OTel.trace_id` → `runs.run_id` (hex string)
- `OTel.span_id` → `spans.span_id` (hex string)
- `OTel.parent_span_id` → `spans.parent_span_id`
- `OTel.attributes["gen_ai.usage.input_tokens"]` → `spans.prompt_tokens`
- `OTel.attributes["gen_ai.usage.output_tokens"]` → `spans.completion_tokens`
- `OTel.attributes["gen_ai.system"]` → `spans.provider` (openai/anthropic/etc)
- `OTel.attributes["gen_ai.request.model"]` → `spans.model`
- All other attributes → `spans.metadata` JSON

**Deduplication:** If `span_id` exists, last-write-wins. Prevents OTel + native SDK double-counting.

---

#### 7.3.2 Authentication (Optional)

When `AGENTWATCH_API_KEY` env var set:
- All `/v1/*` endpoints (ingest + query) require `X-API-Key: <value>` header
- Missing/wrong key → 401 Unauthorized
- When env var empty → no auth (localhost default)

**Rationale:** Prevents same-network span spam in shared dev envs. Read endpoints also gated (cost data is sensitive).

---

### 7.4 Python SDK Design

#### 7.4.1 Installation & Basic Usage

**[Unchanged from v1.0 §7.4]**

```python
pip install agentwatch

import agentwatch
aw = agentwatch.init(url="http://localhost:8000")

# LangChain
chain = agent.with_config(callbacks=[aw.callback_handler])
```

---

#### 7.4.2 LangChain Callback Handler

**[Unchanged from v1.0 §7.4]** — `AgentWatchCallbackHandler` class with `on_llm_start`, `on_llm_end`, `on_tool_start`, `on_tool_end`, `on_chain_error`.

**v2 adjustment:** `_detect_provider(model: str)` now checks:
1. Substring match: `"gpt"` → openai, `"claude"` → anthropic, `"gemini"` → google
2. **NEW:** If model starts with provider prefix from known list → use that provider
3. **NEW:** If not matched, inspect `base_url` if available (for OpenAI-compatible endpoints)

---

#### 7.4.3 NEW: Native Provider Patches

For users NOT using LangChain:

```python
# OpenAI
from openai import OpenAI
client = OpenAI(api_key="...")
aw.patch_openai(client)
# Now all client.chat.completions.create calls auto-tracked

# Anthropic
from anthropic import Anthropic
client = Anthropic(api_key="...")
aw.patch_anthropic(client)

# Bedrock
import boto3
bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
aw.patch_bedrock(bedrock)

# DeepSeek (OpenAI-compatible)
from openai import OpenAI
client = OpenAI(base_url="https://api.deepseek.com", api_key="...")
aw.patch_openai(client, provider="deepseek")

# Kimi/Moonshot (OpenAI-compatible)
client = OpenAI(base_url="https://api.moonshot.cn/v1", api_key="...")
aw.patch_openai(client, provider="moonshot")
```

**Implementation:**
- `patch_openai`: wraps `chat.completions.create` (sync, async, stream)
  - Stream mode: injects `stream_options={"include_usage": True}` if missing
  - Aggregates chunks, extracts final `usage` from last chunk
- `patch_anthropic`: wraps `messages.create` + `messages.stream`
- `patch_bedrock`: wraps `invoke_model` + `invoke_model_with_response_stream`
  - Token extraction per model family registry:
    - Claude: `body["usage"]["input_tokens"]` / `"output_tokens"`
    - Llama: `body["prompt_token_count"]` / `"generation_token_count"`
    - Titan: `body["inputTextTokenCount"]` / `"results"][0]["tokenCount"]`
- `patch_openai(client, provider=X)`: override provider field for OpenAI-compatible APIs

**Dedup with OTel:** Patches add `metadata.source = "native"`. OTel spans have `metadata.source = "otel"`. Server dedup on `span_id` if both present.

---

### 7.5 Frontend — Screen-by-Screen Spec

**[90% unchanged from v1.0 §7.5]**

**v2 additions:**

#### Screen 5: Settings (`/settings`) — NEW toggles

**Section 1: Model Pricing** — [unchanged]

**Section 2: Storage Policy** — [unchanged]

**Section 3: Ingest Options** (NEW)

- **OpenTelemetry endpoint:** Display OTLP endpoint URL for copy-paste into OTel SDK config
  ```
  OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:8000/v1/traces
  ```
- **API Key:** Input field to set/reset `AGENTWATCH_API_KEY` (restart backend required)

---

### 7.6 Real-time WebSocket Design

**[Unchanged from v1.0 §7.6]**

**v2 note added:** Single-process broadcast works for v1. Multi-replica scaling (Redis pub/sub) deferred to v1.1.

---

### 7.7 Docker & Deployment Design

**v1.0 `docker-compose.yml` had:** `db` (postgres) + `backend` + `frontend`.

**v2.0 change:** Backend supports dual DB mode via `DATABASE_URL` env:

```yaml
services:
  db:
    image: postgres:16-alpine
    # ... [unchanged]

  backend:
    environment:
      DATABASE_URL: postgresql://agentwatch:pass@db:5432/agentwatch
      # OR for dev mode without Postgres:
      # DATABASE_URL: sqlite+aiosqlite:///./data/aw.db
      AGENTWATCH_API_KEY: ""  # empty = no auth (localhost default)
      STORE_PROMPTS: "false"
```

**SQLite dev mode usage:**
```bash
# No Postgres needed
export DATABASE_URL=sqlite+aiosqlite:///./aw.db
uvicorn backend.main:app
```

---

## 8. Technical Stack Decision (Updated)

| Layer | v1.0 Choice | v2.0 Adjustment | Reason |
|-------|-------------|-----------------|--------|
| Database | PostgreSQL only | **PostgreSQL (prod) + SQLite (dev)** | Zero-friction local dev without Docker container |
| OTLP support | Not planned | **opentelemetry-proto** package | Differentiator vs Langfuse; captures existing OTel users |
| SDK LangChain-only | Yes | **+ Native patches** (OpenAI, Anthropic, Bedrock, DeepSeek, Kimi) | Captures non-LangChain audience (raw API users) |
| Auth | v1.1 feature | **Optional X-API-Key in v1** | Prevents network spam; gates sensitive cost data on read endpoints |

All other choices (FastAPI, React, Tailwind, Recharts, Docker Compose) unchanged.

---

## 9. User Flows

**[Unchanged from v1.0 §9]** — see original PRD.

---

## 10. Release Plan — Phase by Phase (Updated)

### Phase 0 — Spike (Days 1–2) **[NEW in v2]**

**Goal:** Validate tech choices + new v2 features work before committing to MVP.

**Deliverable:** `spike/` directory with throwaway code + `SPIKE_RESULTS.md` with pass/fail for each question.

**Questions to answer:**

| # | Question | Pass Criterion |
|---|----------|----------------|
| Q1 | FastAPI + Postgres: 100 spans/sec sustained, p95 < 200ms? | Zero connection errors over 60s |
| Q2 | FastAPI + SQLite: survives 100 spans/sec? | p95 < 500ms (or document Postgres-only) |
| Q3 | LangChain callback: token_usage populated for GPT-4o, Claude, Gemini, Bedrock? | All return prompt_tokens + completion_tokens |
| Q4 | Patch `openai.OpenAI`: capture sync + async + stream without breaking? | All 3 modes work, stream includes usage |
| Q5 | Same patch for Anthropic, Bedrock (Claude + Llama), DeepSeek, Kimi? | All emit span with correct provider/model/tokens |
| Q6 | FastAPI accept OTLP/HTTP, map to schema? | OTel trace → `spans` table with parent linkage |
| Q7 | WebSocket → browser: 50 msg/sec, ≥99% delivery? | No disconnects in 5 min |
| Q8 | `docker compose up` clean start on Windows + WSL? | `/health` + dashboard both 200 in 30s |
| Q9 | `X-API-Key` middleware: 401 when set, pass-through when empty? | Both behaviors confirmed |

**Done when:** `SPIKE_RESULTS.md` committed with PASS/FAIL + evidence for each Q.

**If any FAIL:** Amend MVP plan before Phase 1.

---

### Phase 1 — MVP (Week 1: Days 3–9)

**Backend:**
- [All v1.0 tickets] +
- **NEW:** OTLP endpoint (`POST /v1/traces`)
- **NEW:** Dual DB support (Postgres/SQLite via `DATABASE_URL`)
- **NEW:** `X-API-Key` middleware
- **NEW:** Extended model_pricing seed (DeepSeek, Kimi, Bedrock variants)

**SDK:**
- [All v1.0 tickets] +
- **NEW:** `patch_openai`, `patch_anthropic`, `patch_bedrock` functions
- **NEW:** `patch_openai(client, provider="deepseek"|"moonshot")` for OpenAI-compatible APIs

**Frontend:**
- [Unchanged from v1.0]

---

### Phase 2 — Core Features (Week 2: Days 10–16)

**[Unchanged from v1.0 §10 Phase 2]**

---

### Phase 3 — Polish + Launch (Week 3: Days 17–21)

**[Unchanged from v1.0 §10 Phase 3]**

**v2 addition to README:**
- "Works with OpenTelemetry" section with OTLP endpoint setup
- "No LangChain Required" section with native patch examples

---

### Phase 4 — v1.1 (Post-Launch)

**v1.0 roadmap items:**
- JS/TS SDK
- CrewAI native integration
- Alert rules
- Team auth
- Export CSV/JSON
- Prompt storage opt-in

**v2.0 items moved from v1.1 → v1.0:**
- ~~OTel compat~~ ✅ (now v1)
- ~~SQLite mode~~ ✅ (now v1)
- ~~API auth~~ ✅ (now v1)

**v2.0 NEW v1.1 candidates:**
- Redis pub/sub for multi-replica WS broadcast
- Bedrock streaming with token aggregation (currently sync only in spike)
- PII redaction regex filters on input/output_preview

---

## 11. Ticket Breakdown (GitHub Issues)

**[v1.0 Milestone 0–5 tickets remain]**

**v2.0 NEW tickets:**

### Milestone 0 — Spike (added)

| # | Title | Size |
|---|-------|------|
| 1-3 | [v1.0 spike tickets] | S |
| 4 | [SPIKE] Validate OTLP decode + GenAI semconv mapping | M |
| 5 | [SPIKE] Validate SQLite + aiosqlite throughput | S |
| 6 | [SPIKE] Validate native OpenAI patch (sync/async/stream with usage) | M |
| 7 | [SPIKE] Validate Bedrock token extraction (Claude vs Llama) | M |

### Milestone 1 — MVP Backend (added)

| # | Title | Size |
|---|-------|------|
| ... | [v1.0 backend tickets] | ... |
| 12a | POST /v1/traces — OTLP protobuf decode + span insert | L |
| 12b | Dual DB engine: Postgres + SQLite via DATABASE_URL | M |
| 12c | X-API-Key middleware on all /v1/* routes | S |
| 12d | Extended model_pricing seed (15 new models) | S |

### Milestone 2 — MVP SDK (added)

| # | Title | Size |
|---|-------|------|
| ... | [v1.0 SDK tickets] | ... |
| 19a | patch_openai: sync + async + stream with usage injection | L |
| 19b | patch_anthropic: sync + stream | M |
| 19c | patch_bedrock: per-model-family token extractor registry | L |
| 19d | patch_openai with provider override (DeepSeek, Kimi) | S |

---

## 12. Success Metrics

**[Unchanged from v1.0 §12]**

**v2 addition:** Track OTel adoption via:
- GitHub issues asking "how do I use with OTel?" (indicates awareness)
- `metadata.source='otel'` span count in live demo DB (usage signal)

---

## 13. Risks & Design Adjustments

### 13.1 Design Adjustments from Phase 0 Spike (NEW)

These emerged from spike plan; fold into MVP:

1. **Orphan span handling:** Spans may arrive before parent (async batches). Frontend tree builder must handle missing parent_span_id gracefully. Backend: no FK constraint on `parent_span_id`.

2. **Cost calculation: server-side only.** Client-side requires shipping pricing table to SDK (versioning hell). Follow Langfuse/Helicone precedent.

3. **OTel + native dedup strategy:** `span_id` uniqueness, last-write-wins. If both OTel + native SDK active, server keeps most recent. Document: "Don't use both on same process."

4. **Bedrock token format varies per model.** MVP needs `bedrock_token_extractor(model_id, response_body)` registry, not single function. Spike validates Claude + Llama; MVP adds Titan/Cohere.

5. **OpenAI streaming requires `stream_options.include_usage=True`.** Patch must inject if missing, else tokens dropped silently. High-impact failure; explicitly tested in spike.

6. **DeepSeek/Kimi provider detection via base_url.** PRD v1 `_detect_provider` substring-only. v2: check `client.base_url` for `deepseek.com` / `moonshot.cn` / `bedrock` / etc.

7. **Missing model_pricing entries for new providers.** Spike writes complete seed list (15 models). MVP inserts at startup or cost calc returns 0.

8. **`run_id` idempotency on conflict.** Spike tests: POST same `run_id` twice → 200 with existing record (idempotent), not 409. SDK retry-safe.

9. **WebSocket scaling.** Single-process broadcast OK for v1. Multi-replica breaks (no shared state). v1.1: Redis pub/sub or NATS. Document limitation.

10. **Auth gates read endpoints too.** v1 PRD said "no auth" but API key should gate `/v1/runs`, `/v1/metrics/*` when set — cost data is sensitive. Spike validates both read + write.

---

### 13.2 Risks & Mitigations

**[Unchanged from v1.0 §13]** — LangChain API changes, Docker Windows issues, Railway limits, etc.

---

## 14. Open Questions

**[v1.0 questions remain]**

**v2.0 NEW questions:**

| # | Question | Owner | Due |
|---|----------|-------|-----|
| 6 | Should OTel endpoint be separate port (4318) or same backend (/v1/traces)? | Rahul | Phase 0 |
| 7 | SQLite: use WAL mode for concurrent reads? Or document "dev only, single-process"? | Rahul | Phase 0 |
| 8 | Bedrock streaming: does `invoke_model_with_response_stream` return usage in final chunk? | Rahul | Phase 0 Q5 |
| 9 | Should native patches be opt-in (explicit `aw.patch_X()`) or auto-patch on import? | Rahul | Phase 1 |

---

## 15. Appendix — Competitor Deep Dive

**[Unchanged from v1.0 §15]**

**v2 competitive positioning update:**

| Feature | LangSmith | Langfuse | **AgentWatch v2** |
|---------|-----------|----------|-------------------|
| OpenTelemetry OTLP | ❌ | ✅ (partial) | **✅ (full GenAI semconv)** |
| Non-LangChain SDK | Partial | ✅ | **✅ (5 providers patched)** |
| SQLite dev mode | ❌ | ❌ | **✅** |
| Bedrock support | ✅ | Partial | **✅ (Claude, Llama, Titan tested)** |
| Setup complexity | Low | Medium-High | **Very Low (1 command)** |

---

*PRD v2.0 authored May 26, 2026 | AgentWatch Phase 0 Spike + MVP | Rahul Rachhoya*

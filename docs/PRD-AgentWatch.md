# PRD: AgentWatch — Open-Source LLM Agent Monitoring Dashboard

**Author:** Rahul Rachhoya  
**Status:** Draft  
**Version:** 1.0  
**Date:** May 26, 2026  
**Type:** Greenfield OSS Project  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Background & Why Now](#2-background--why-now)
3. [Problem Statement](#3-problem-statement)
4. [Goals & Non-Goals](#4-goals--non-goals)
5. [Target Users & Market Segments](#5-target-users--market-segments)
6. [Value Proposition & Competitive Analysis](#6-value-proposition--competitive-analysis)
7. [Solution — Full Feature Specification](#7-solution--full-feature-specification)
   - 7.1 System Architecture
   - 7.2 Data Model & Schema
   - 7.3 API Design (All Endpoints)
   - 7.4 Python SDK Design
   - 7.5 Frontend — Screen-by-Screen Spec
   - 7.6 Real-time WebSocket Design
   - 7.7 Docker & Deployment Design
8. [Technical Stack Decision](#8-technical-stack-decision)
9. [User Flows](#9-user-flows)
10. [Release Plan — Phase by Phase](#10-release-plan--phase-by-phase)
11. [Ticket Breakdown (GitHub Issues)](#11-ticket-breakdown-github-issues)
12. [Success Metrics](#12-success-metrics)
13. [Risks & Mitigations](#13-risks--mitigations)
14. [Open Questions](#14-open-questions)
15. [Appendix — Competitor Deep Dive](#15-appendix--competitor-deep-dive)

---

## 1. Executive Summary

**AgentWatch** is a self-hostable, open-source LLM agent monitoring dashboard. It gives AI engineers real-time visibility into every agent run — cost per session, token usage, latency per step, tool call success rates, and error traces — across any agent framework (LangGraph, CrewAI, AutoGen, bare OpenAI API).

**Core hook:** LangSmith costs $39/month per seat. AgentWatch is free. One `docker-compose up` and a 3-line Python SDK install. Zero data leaves your infrastructure.

**Why it matters for Rahul's resume:** AgentWatch directly mirrors the LangSmith observability stack he built at Careers360 — except now it's open-source, public, live-demo-able, and positioned to earn GitHub stars from the AI engineering community.

---

## 2. Background & Why Now

### The LLM Production Explosion

In 2024–2026, the number of teams running LLM agents in production has grown 10x. Every company building on LangChain, LangGraph, CrewAI, or raw OpenAI APIs now has the same operational problem:

- **Cost tracking:** "We spent $X on OpenAI this month — but which agents are burning it?"
- **Latency debugging:** "Why is our agent slow on Tuesdays?"
- **Error tracing:** "The agent gave a wrong answer — which step failed?"
- **Quality regression:** "Did our last prompt change break accuracy?"

### Existing Tools Are Paid or Partial

| Tool | Problem |
|------|---------|
| LangSmith | $39/seat/month. Usage-based pricing gets expensive fast. Data sent to Langchain's servers. |
| Weights & Biases (Weave) | Great for ML experiments, awkward for agent traces. Pricing opaque. |
| Helicone | Proxy-based — only captures OpenAI API calls, not agent-level flows. |
| Langfuse | Open source ✅ but complex setup; TypeScript-first, limited Python SDK quality. |
| Datadog LLM Observability | Enterprise pricing ($$$). Overkill for indie teams. |

### The Gap

There is no **simple, Python-first, truly self-hostable** agent monitoring tool with:
1. One-command Docker install
2. A 3-line Python SDK
3. A real-time dashboard that "just works"
4. 100% free, no API keys, no phone home

### Why Rahul Can Build This

- He built a production LangSmith stack at Careers360 tracking 10K+ Voice AI sessions
- He knows exactly what metrics matter (cost/session, p95 latency, hallucination flags)
- He has LangGraph, CrewAI, and AWS Bedrock experience — he can write the integrations himself

---

## 3. Problem Statement

> **AI engineers running LLM agents in production have no affordable, self-hosted way to answer three questions in real time: How much did this agent run cost? Which step was slow? What went wrong?**

**Who is blocked:** Individual AI engineers, small AI startups, indie hackers building LLM-powered products.

**What they do today:** `print()` statements, manually checking OpenAI usage dashboards, paying $39+/month for LangSmith, or building custom logging from scratch.

**The pain:** Every engineering hour spent on custom logging is an hour not spent on product features. And without structured observability, production LLM bugs are nearly impossible to debug.

---

## 4. Goals & Non-Goals

### Goals

- **G1:** Allow any Python LLM developer to start monitoring agent runs in under 5 minutes
- **G2:** Track cost, latency, token usage, and tool calls per agent run out of the box
- **G3:** Provide a real-time dashboard (no refresh needed) showing live agent runs
- **G4:** Support LangChain, LangGraph, CrewAI, and raw OpenAI/Anthropic API calls via a Python SDK
- **G5:** Run entirely via `docker-compose up` — zero cloud dependencies
- **G6:** Achieve 50+ GitHub stars within 30 days of launch
- **G7:** Have a live public demo at a permanent URL for portfolio use

### Non-Goals

- **NG1:** NOT building a proxy-based solution (no MITM on API calls — SDK-only)
- **NG2:** NOT supporting JavaScript/TypeScript SDK in v1 (Python only)
- **NG3:** NOT building user authentication/teams in v1 (single-user, local use)
- **NG4:** NOT replacing LangSmith's prompt playground or dataset management features
- **NG5:** NOT building alerting/PagerDuty integrations in v1
- **NG6:** NOT storing actual LLM prompts/responses by default (privacy-first — opt-in only)

---

## 5. Target Users & Market Segments

### Primary Segment: The Solo AI Engineer / Indie AI Hacker

**Profile:**
- Builds LLM-powered apps solo or in a 2-5 person team
- Spends $50-500/month on LLM API costs
- Uses LangChain or LangGraph for orchestration
- Frustrated by LangSmith pricing for personal/side projects
- Actively searches GitHub and Reddit for OSS tools

**Jobs-to-be-done:**
- *"I need to know which of my agent's 6 steps is causing the 12s latency"*
- *"I need to see my OpenAI costs per user session, not just monthly total"*
- *"I need to replay a failing agent run to debug it"*

**Where they hang out:** r/LocalLLaMA, r/MachineLearning, Hacker News, LangChain Discord

---

### Secondary Segment: Small AI Startup (5-20 engineers)

**Profile:**
- Series A or pre-seed startup building AI-native product
- Has a "we don't send data to third-party analytics tools" policy
- Needs cost attribution by customer/tenant
- Values open-source for security auditing

**Jobs-to-be-done:**
- *"Our LLM costs are 30% of our AWS bill and we don't know which feature is causing it"*
- *"We need to show our investors cost-per-query metrics"*

---

### Tertiary Segment: AI Engineering Students & Bootcamp Grads

**Profile:**
- Learning to build LLM apps
- Wants production-grade tooling for portfolio projects
- Can't afford paid observability tools

**Value:** GitHub star contributors, community evangelists, word-of-mouth.

---

## 6. Value Proposition & Competitive Analysis

### Value Curve

| Dimension | LangSmith | Langfuse | Helicone | **AgentWatch** |
|-----------|-----------|---------|---------|---------------|
| Price | $39/seat/month | Free (cloud) / self-hosted | $0-$120/month | **Free forever (self-hosted)** |
| Setup complexity | Low | Medium | Low | **Very low (1 command)** |
| Python SDK quality | Excellent | Good | N/A | **Excellent** |
| Self-hosted | ❌ | ✅ | ❌ | **✅** |
| Data privacy | ❌ (cloud) | ✅ | ❌ | **✅ (100%)** |
| Real-time dashboard | ✅ | ✅ | ✅ | **✅** |
| LangGraph support | ✅ | ✅ | ❌ | **✅** |
| CrewAI support | ✅ | Partial | ❌ | **✅** |
| Bedrock support | Partial | Partial | ❌ | **✅ (built by someone who uses it)** |
| Docker Compose | ❌ | ✅ (complex) | ❌ | **✅ (simple)** |
| GitHub stars (Jun 2026) | 6.1K | 8.2K | 2.3K | **Target: 200 in 30 days** |

### AgentWatch's Unique Angle

**"Built by an AI engineer who was frustrated by LangSmith pricing. Everything LangSmith does for teams using OpenAI, AgentWatch does for solo engineers and small teams using any LLM, for free, on your own machine."**

The positioning is not "better than LangSmith" — it's "LangSmith but self-hosted and free for indie builders".

---

## 7. Solution — Full Feature Specification

### 7.1 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Your Python App                         │
│                                                             │
│  import agentwatch                                          │
│  aw = agentwatch.Client("http://localhost:8000")            │
│  chain = agent.with_config(callbacks=[aw.callback_handler]) │
│                                     │                       │
└─────────────────────────────────────┼───────────────────────┘
                                      │ HTTP POST /v1/spans
                                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  AgentWatch Backend (FastAPI)                │
│                                                             │
│  ┌──────────────┐  ┌────────────────┐  ┌─────────────────┐ │
│  │  Ingest API  │  │  Query API     │  │  WebSocket Hub  │ │
│  │  /v1/spans   │  │  /v1/runs      │  │  /ws/runs       │ │
│  │  /v1/runs    │  │  /v1/metrics   │  │  /ws/metrics    │ │
│  └──────┬───────┘  └───────┬────────┘  └────────┬────────┘ │
│         │                  │                     │          │
│         ▼                  ▼                     ▼          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │               PostgreSQL + pgvector                  │   │
│  │  tables: runs, spans, tools, metrics_cache           │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────┐
│                 AgentWatch Frontend (React/TS)               │
│                                                             │
│  / Dashboard → Live Runs + Cost Chart + Latency Chart       │
│  /runs       → Run List (filterable/sortable)               │
│  /runs/:id   → Run Detail + Span Waterfall                  │
│  /metrics    → Aggregated metrics, time-series charts       │
│  /settings   → Config: model costs, retention policy        │
└─────────────────────────────────────────────────────────────┘
```

**All three components run in Docker Compose on a single machine. No external services required.**

---

### 7.2 Data Model & Schema

#### Table: `runs`
The top-level unit. One row = one agent invocation.

```sql
CREATE TABLE runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          TEXT UNIQUE NOT NULL,       -- client-provided idempotency key
    name            TEXT NOT NULL,              -- e.g. "career-counselor-agent"
    session_id      TEXT,                       -- group runs by user session
    tags            TEXT[] DEFAULT '{}',        -- e.g. ['production', 'voice-ai']
    
    -- Timing
    started_at      TIMESTAMPTZ NOT NULL,
    ended_at        TIMESTAMPTZ,
    duration_ms     INTEGER,                    -- computed on end
    
    -- Status
    status          TEXT NOT NULL DEFAULT 'running',  -- running | success | error
    error_message   TEXT,
    
    -- Aggregated metrics (denormalized for fast dashboard queries)
    total_tokens    INTEGER DEFAULT 0,
    prompt_tokens   INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_cost_usd  NUMERIC(10, 6) DEFAULT 0,
    span_count      INTEGER DEFAULT 0,
    tool_call_count INTEGER DEFAULT 0,
    
    -- Metadata
    metadata        JSONB DEFAULT '{}',         -- arbitrary key-value from user
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_runs_started_at ON runs(started_at DESC);
CREATE INDEX idx_runs_session_id ON runs(session_id);
CREATE INDEX idx_runs_status ON runs(status);
CREATE INDEX idx_runs_tags ON runs USING GIN(tags);
```

---

#### Table: `spans`
One row = one LLM call or tool call inside a run.

```sql
CREATE TABLE spans (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    span_id         TEXT UNIQUE NOT NULL,       -- client-provided
    run_id          TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    parent_span_id  TEXT,                       -- null = root span; non-null = nested
    
    -- What kind of span
    span_type       TEXT NOT NULL,              -- llm | tool | chain | retriever | custom
    name            TEXT NOT NULL,              -- e.g. "gpt-4o", "search_tool", "intent_classifier"
    
    -- LLM-specific fields (null for tool spans)
    model           TEXT,                       -- e.g. "gpt-4o", "claude-3-5-sonnet"
    provider        TEXT,                       -- openai | anthropic | bedrock | google | other
    prompt_tokens   INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens    INTEGER DEFAULT 0,
    cost_usd        NUMERIC(10, 6) DEFAULT 0,
    
    -- Optional: store prompts (off by default, enabled via AGENTWATCH_STORE_PROMPTS=true)
    input_preview   TEXT,                       -- first 500 chars of input (truncated)
    output_preview  TEXT,                       -- first 500 chars of output (truncated)
    
    -- Timing
    started_at      TIMESTAMPTZ NOT NULL,
    ended_at        TIMESTAMPTZ,
    duration_ms     INTEGER,
    
    -- Status
    status          TEXT NOT NULL DEFAULT 'running',  -- running | success | error
    error_type      TEXT,                       -- e.g. "RateLimitError", "ContextLengthError"
    error_message   TEXT,
    
    -- Tool-specific fields (null for LLM spans)
    tool_name       TEXT,
    tool_input      JSONB,
    tool_output     JSONB,
    
    -- Metadata
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_spans_run_id ON spans(run_id);
CREATE INDEX idx_spans_started_at ON spans(started_at DESC);
CREATE INDEX idx_spans_model ON spans(model);
CREATE INDEX idx_spans_span_type ON spans(span_type);
```

---

#### Table: `metrics_hourly` (materialized aggregates)
Pre-computed for fast dashboard queries.

```sql
CREATE TABLE metrics_hourly (
    hour            TIMESTAMPTZ NOT NULL,
    run_count       INTEGER DEFAULT 0,
    success_count   INTEGER DEFAULT 0,
    error_count     INTEGER DEFAULT 0,
    total_tokens    BIGINT DEFAULT 0,
    total_cost_usd  NUMERIC(12, 4) DEFAULT 0,
    avg_duration_ms INTEGER,
    p95_duration_ms INTEGER,
    PRIMARY KEY (hour)
);
```

---

#### Table: `model_pricing`
Reference table — used to auto-calculate cost from token counts.

```sql
CREATE TABLE model_pricing (
    model           TEXT PRIMARY KEY,
    provider        TEXT NOT NULL,
    input_cost_per_1k_tokens  NUMERIC(8, 6),   -- $ per 1K input tokens
    output_cost_per_1k_tokens NUMERIC(8, 6),   -- $ per 1K output tokens
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Seed data (insert at startup)
INSERT INTO model_pricing VALUES
    ('gpt-4o',              'openai',    0.005,   0.015),
    ('gpt-4o-mini',         'openai',    0.00015, 0.0006),
    ('gpt-4-turbo',         'openai',    0.01,    0.03),
    ('gpt-3.5-turbo',       'openai',    0.0005,  0.0015),
    ('claude-3-5-sonnet',   'anthropic', 0.003,   0.015),
    ('claude-3-haiku',      'anthropic', 0.00025, 0.00125),
    ('claude-3-opus',       'anthropic', 0.015,   0.075),
    ('gemini-1.5-pro',      'google',    0.00125, 0.005),
    ('gemini-1.5-flash',    'google',    0.000075,0.0003),
    ('mistral-7b',          'mistral',   0.00025, 0.00025),
    ('mixtral-8x7b',        'mistral',   0.0007,  0.0007);
```

---

### 7.3 API Design (All Endpoints)

Base URL: `http://localhost:8000/api/v1`

---

#### Ingest Endpoints (SDK → Backend)

**POST `/runs`** — Create a new run

```json
// Request
{
  "run_id": "run_abc123",             // client-generated UUID or nanoid
  "name": "career-counselor-agent",
  "session_id": "user_session_xyz",   // optional — group by user
  "tags": ["production", "voice-ai"], // optional
  "started_at": "2026-05-26T10:00:00Z",
  "metadata": { "user_id": "u_123", "channel": "voice" }
}

// Response 201
{
  "data": { "run_id": "run_abc123", "status": "running" }
}
```

---

**PATCH `/runs/{run_id}`** — Update run on completion or error

```json
// Request
{
  "status": "success",            // or "error"
  "ended_at": "2026-05-26T10:00:12Z",
  "error_message": null           // or error string
}

// Response 200
{
  "data": { "run_id": "run_abc123", "status": "success", "duration_ms": 12000 }
}
```

---

**POST `/spans`** — Ingest one span (LLM call or tool call)

```json
// Request — LLM span
{
  "span_id": "span_def456",
  "run_id": "run_abc123",
  "parent_span_id": null,
  "span_type": "llm",
  "name": "claude-3-5-sonnet",
  "model": "claude-3-5-sonnet",
  "provider": "anthropic",
  "prompt_tokens": 1250,
  "completion_tokens": 340,
  "started_at": "2026-05-26T10:00:01Z",
  "ended_at": "2026-05-26T10:00:03.2Z",
  "status": "success",
  "input_preview": "You are a career counselor. User says: I want to be a data...",
  "output_preview": "Based on your background in AI engineering, I recommend..."
}

// Request — Tool span
{
  "span_id": "span_ghi789",
  "run_id": "run_abc123",
  "parent_span_id": "span_def456",
  "span_type": "tool",
  "name": "search_courses",
  "tool_name": "search_courses",
  "tool_input": { "query": "data science bootcamp", "location": "india" },
  "tool_output": { "results": ["...", "..."], "count": 12 },
  "started_at": "2026-05-26T10:00:02Z",
  "ended_at": "2026-05-26T10:00:02.8Z",
  "status": "success"
}

// Response 201
{
  "data": { "span_id": "span_def456", "cost_usd": 0.0245 }
}
```

**POST `/spans/batch`** — Ingest multiple spans in one HTTP call (performance optimization)

```json
// Request
{
  "spans": [ { ...span1 }, { ...span2 }, { ...span3 } ]
}

// Response 201
{
  "data": { "created": 3, "failed": 0 }
}
```

---

#### Query Endpoints (Frontend → Backend)

**GET `/runs`** — List runs (paginated, filterable)

Query params:
- `?limit=20&cursor=eyJ...` — pagination
- `?status=error` — filter by status
- `?tag=production` — filter by tag
- `?session_id=xyz` — filter by session
- `?from=2026-05-01&to=2026-05-26` — date range
- `?sort=-started_at` — sort (default: newest first)

```json
// Response 200
{
  "data": [
    {
      "run_id": "run_abc123",
      "name": "career-counselor-agent",
      "status": "success",
      "started_at": "2026-05-26T10:00:00Z",
      "duration_ms": 12000,
      "total_tokens": 1590,
      "total_cost_usd": 0.0245,
      "span_count": 4,
      "tool_call_count": 2,
      "tags": ["production"]
    }
  ],
  "meta": {
    "next_cursor": "eyJ...",
    "has_more": true,
    "total_count": 1420
  }
}
```

---

**GET `/runs/{run_id}`** — Get full run detail with all spans

```json
// Response 200
{
  "data": {
    "run_id": "run_abc123",
    "name": "career-counselor-agent",
    "status": "success",
    "started_at": "2026-05-26T10:00:00Z",
    "ended_at": "2026-05-26T10:00:12Z",
    "duration_ms": 12000,
    "total_tokens": 1590,
    "total_cost_usd": 0.0245,
    "tags": ["production"],
    "metadata": { "user_id": "u_123" },
    "spans": [
      {
        "span_id": "span_def456",
        "span_type": "llm",
        "name": "claude-3-5-sonnet",
        "model": "claude-3-5-sonnet",
        "started_at": "...",
        "duration_ms": 2200,
        "prompt_tokens": 1250,
        "completion_tokens": 340,
        "cost_usd": 0.0245,
        "status": "success",
        "children": [
          {
            "span_id": "span_ghi789",
            "span_type": "tool",
            "name": "search_courses",
            "duration_ms": 800,
            "status": "success"
          }
        ]
      }
    ]
  }
}
```

---

**GET `/metrics/summary`** — Dashboard summary card values

Query params: `?from=2026-05-19&to=2026-05-26` (default: last 7 days)

```json
// Response 200
{
  "data": {
    "period": "last_7_days",
    "total_runs": 342,
    "success_rate": 0.973,
    "total_cost_usd": 18.42,
    "avg_cost_per_run": 0.054,
    "total_tokens": 1842000,
    "avg_duration_ms": 3840,
    "p95_duration_ms": 9200,
    "error_count": 9,
    "top_error": "RateLimitError",
    "most_used_model": "claude-3-5-sonnet",
    "cost_by_model": {
      "claude-3-5-sonnet": 14.20,
      "gpt-4o-mini": 4.22
    }
  }
}
```

---

**GET `/metrics/timeseries`** — Time-series data for charts

Query params:
- `?metric=cost` — cost | tokens | runs | latency | errors
- `?granularity=hour` — hour | day
- `?from=...&to=...`

```json
// Response 200
{
  "data": {
    "metric": "cost",
    "granularity": "hour",
    "points": [
      { "timestamp": "2026-05-26T00:00:00Z", "value": 0.42 },
      { "timestamp": "2026-05-26T01:00:00Z", "value": 0.18 },
      ...
    ]
  }
}
```

---

**GET `/metrics/models`** — Usage breakdown by model

```json
// Response 200
{
  "data": [
    {
      "model": "claude-3-5-sonnet",
      "provider": "anthropic",
      "run_count": 180,
      "total_tokens": 1200000,
      "total_cost_usd": 14.20,
      "avg_latency_ms": 2100,
      "error_rate": 0.011
    }
  ]
}
```

---

**GET `/health`** — Health check (used by Docker and monitoring)

```json
// Response 200
{ "status": "ok", "db": "connected", "version": "1.0.0" }
```

---

### 7.4 Python SDK Design

The SDK is what makes or breaks adoption. It must be **3 lines to integrate**.

#### Installation
```bash
pip install agentwatch
```

#### Basic Usage — 3 lines
```python
import agentwatch

# Initialize (once at app startup)
aw = agentwatch.init(url="http://localhost:8000")

# Use with LangChain/LangGraph — 1 extra line in your existing code
chain = your_agent.with_config(callbacks=[aw.callback_handler])
result = chain.invoke({"input": "Help me find a job"})
```

That's it. Every LLM call inside `chain` is now tracked.

---

#### SDK Internals — Class Design

```python
# agentwatch/__init__.py

class AgentWatch:
    def __init__(self, url: str, batch_size: int = 10, flush_interval: float = 2.0):
        """
        url: AgentWatch backend URL
        batch_size: flush spans when this many are queued (default 10)
        flush_interval: flush every N seconds even if batch_size not reached
        """
        self.url = url.rstrip("/")
        self._queue: list[dict] = []
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()
    
    @property
    def callback_handler(self) -> "AgentWatchCallbackHandler":
        """Returns a LangChain-compatible callback handler."""
        return AgentWatchCallbackHandler(client=self)
    
    def track_run(self, name: str, session_id: str = None, tags: list = None, metadata: dict = None):
        """Context manager for manual run tracking."""
        return RunContext(client=self, name=name, session_id=session_id, tags=tags, metadata=metadata)
    
    def _flush_loop(self):
        """Background thread: flushes span queue every flush_interval seconds."""
        while True:
            time.sleep(self._flush_interval)
            self._flush()
    
    def _flush(self):
        """Send queued spans to backend in a single batch request."""
        if not self._queue:
            return
        batch, self._queue = self._queue[:], []
        try:
            requests.post(f"{self.url}/api/v1/spans/batch", json={"spans": batch}, timeout=5)
        except Exception:
            pass  # Never crash the user's app due to observability failure


def init(url: str = "http://localhost:8000", **kwargs) -> AgentWatch:
    """Module-level init for quick setup."""
    global _default_client
    _default_client = AgentWatch(url=url, **kwargs)
    return _default_client
```

---

#### LangChain Callback Handler

```python
class AgentWatchCallbackHandler(BaseCallbackHandler):
    """Drop-in LangChain callback handler. Works with LangGraph, CrewAI (via LangChain), chains."""
    
    def on_chain_start(self, serialized, inputs, *, run_id, parent_run_id=None, **kwargs):
        """Called when a LangChain chain/agent starts."""
        # If no parent → this is the root run → create a run record
        if parent_run_id is None:
            self.client._create_run(
                run_id=str(run_id),
                name=serialized.get("name", "chain"),
                started_at=datetime.utcnow().isoformat()
            )
        # Always create a span
        self.client._start_span(
            span_id=str(run_id),
            run_id=str(parent_run_id or run_id),
            parent_span_id=str(parent_run_id) if parent_run_id else None,
            span_type="chain",
            name=serialized.get("name", "chain")
        )
    
    def on_llm_start(self, serialized, prompts, *, run_id, parent_run_id=None, **kwargs):
        model = serialized.get("kwargs", {}).get("model_name", "unknown")
        self.client._start_span(
            span_id=str(run_id),
            run_id=str(parent_run_id or run_id),
            parent_span_id=str(parent_run_id) if parent_run_id else None,
            span_type="llm",
            name=model,
            model=model,
            provider=self._detect_provider(model),
            input_preview=prompts[0][:500] if prompts else None
        )
    
    def on_llm_end(self, response, *, run_id, **kwargs):
        # Extract token usage from LLMResult
        usage = response.llm_output.get("token_usage", {}) if response.llm_output else {}
        output_text = response.generations[0][0].text if response.generations else ""
        self.client._end_span(
            span_id=str(run_id),
            status="success",
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            output_preview=output_text[:500]
        )
    
    def on_tool_start(self, serialized, input_str, *, run_id, parent_run_id=None, **kwargs):
        self.client._start_span(
            span_id=str(run_id),
            run_id=str(parent_run_id or run_id),
            parent_span_id=str(parent_run_id) if parent_run_id else None,
            span_type="tool",
            name=serialized.get("name", "tool"),
            tool_name=serialized.get("name", "tool"),
            tool_input={"input": input_str}
        )
    
    def on_tool_end(self, output, *, run_id, **kwargs):
        self.client._end_span(span_id=str(run_id), status="success", tool_output={"output": str(output)[:500]})
    
    def on_chain_error(self, error, *, run_id, **kwargs):
        self.client._end_span(span_id=str(run_id), status="error", error_message=str(error))
    
    def on_llm_error(self, error, *, run_id, **kwargs):
        self.client._end_span(span_id=str(run_id), status="error", error_type=type(error).__name__, error_message=str(error))
    
    def _detect_provider(self, model: str) -> str:
        if "gpt" in model or "o1" in model or "o3" in model: return "openai"
        if "claude" in model: return "anthropic"
        if "gemini" in model: return "google"
        if "mistral" in model or "mixtral" in model: return "mistral"
        if "bedrock" in model: return "bedrock"
        return "other"
```

---

#### Manual Context Manager (for non-LangChain users)

```python
# For people using raw OpenAI/Anthropic API — wrap manually
with aw.track_run("my-agent", tags=["production"], metadata={"user": "u_123"}) as run:
    with run.span("gpt-4o", span_type="llm") as span:
        response = openai_client.chat.completions.create(...)
        span.record_tokens(
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            model="gpt-4o"
        )
```

---

### 7.5 Frontend — Screen-by-Screen Spec

**Tech:** React 18 + TypeScript + Vite + Tailwind CSS + shadcn/ui + Recharts

---

#### Screen 1: Dashboard (default `/`)

**Layout:** Top nav → 4 summary cards → 2 charts side by side → Live Runs table

**Summary Cards (top row):**
| Card | Value | Sub-text |
|------|-------|---------|
| Total Runs | 1,420 | ↑ 12% vs last week |
| Total Cost | $18.42 | $0.013 avg/run |
| Success Rate | 97.3% | 39 errors |
| Avg Latency | 3.8s | p95: 9.2s |

**Charts (middle row):**
- Left: Cost over time (line chart, Recharts) — selectable: 24h / 7d / 30d
- Right: Run volume (bar chart) — stacked by status (success/error)

**Live Runs Table (bottom):**
Columns: Run Name | Status | Started | Duration | Tokens | Cost | Tags  
- Real-time: new rows appear via WebSocket without page refresh
- Click any row → go to Run Detail screen
- Status pills: green=success, red=error, blue=running (animated pulse)
- Sortable columns
- Search bar: filter by run name

---

#### Screen 2: Run List (`/runs`)

Full paginated list of all runs.

**Filters sidebar:**
- Status: All / Success / Error / Running
- Date range picker
- Tags multi-select
- Model filter

**Table columns:**
Run ID (short) | Name | Status | Started At | Duration | Total Cost | Tokens | Spans | Tags

**Pagination:** Load more button (cursor-based, 20 runs/page)

---

#### Screen 3: Run Detail (`/runs/:runId`)

The most important screen — drill into one agent run.

**Header:** Run name, status badge, start time, total duration, total cost, total tokens

**Tab 1: Span Waterfall (default tab)**

Gantt-chart style timeline showing all spans:
```
|-- career-counselor-agent (12,000ms) ─────────────────────────────────|
  |-- intent-classifier (claude-3-haiku) (340ms) ──|
  |-- knowledge-retriever (pgvector) (210ms) ─────|
  |-- counselor-agent (claude-3-5-sonnet) (9,200ms) ──────────────────|
      |-- search_courses tool (800ms) ────|
      |-- search_jobs tool (620ms) ─────|
  |-- roadmap-generator (gpt-4o-mini) (2,100ms) ──────────|
```

Each bar is clickable → shows details panel on right:
- Model, tokens, cost, latency
- Input preview, output preview (if STORE_PROMPTS enabled)
- Error message (if error)

**Tab 2: Metrics**
- Token breakdown: prompt vs completion (donut chart)
- Cost breakdown by span (horizontal bar chart)
- Tool call list: name, input, output, duration

**Tab 3: Raw JSON**
Full run + spans data as formatted JSON. "Copy to clipboard" button.

---

#### Screen 4: Metrics (`/metrics`)

Deep analytics view.

**Section 1: Cost Attribution**
- Cost by model (bar chart)
- Cost by tag (bar chart)
- Cost over time (area chart, 30d)

**Section 2: Latency Analysis**
- p50 / p95 / p99 latency over time
- Slowest runs table (Top 10)

**Section 3: Error Analysis**
- Errors over time (bar chart)
- Error type breakdown (pie chart)
- Recent errors table with link to run

**Section 4: Model Usage**
- Table: Model | Runs | Total Tokens | Total Cost | Avg Latency | Error Rate
- Sortable, filterable

---

#### Screen 5: Settings (`/settings`)

**Section 1: Model Pricing**  
Editable table of input/output cost per 1K tokens per model.  
"Reset to defaults" button.  
"Add custom model" form.

**Section 2: Storage Policy**  
Toggle: Store prompt/response previews (default OFF)  
Input: Retention period in days (default 30)  
"Purge old runs" button with confirmation

**Section 3: About**  
Version number, links to GitHub, docs, changelog.

---

### 7.6 Real-time WebSocket Design

The dashboard shows live agent runs without refreshing. This requires a WebSocket connection from the browser to the backend.

**WebSocket endpoint:** `ws://localhost:8000/ws`

**Connection flow:**
```
Browser connects → backend registers connection
Agent SDK sends POST /v1/spans → backend saves to DB → broadcasts to all WS clients
Browser receives message → React state updates → UI re-renders
```

**Message types sent from backend to browser:**

```json
// New run started
{
  "type": "run_started",
  "data": { "run_id": "...", "name": "...", "started_at": "...", "status": "running" }
}

// Run completed
{
  "type": "run_completed",
  "data": { "run_id": "...", "status": "success", "duration_ms": 12000, "total_cost_usd": 0.0245 }
}

// New span in existing run
{
  "type": "span_created",
  "data": { "run_id": "...", "span_id": "...", "span_type": "llm", "name": "..." }
}

// Metrics update (sent every 5 seconds)
{
  "type": "metrics_update",
  "data": { "total_runs_today": 342, "total_cost_today": 18.42 }
}
```

**Backend implementation (FastAPI):**

```python
from fastapi import WebSocket
from typing import Set

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active_connections.add(ws)
    
    async def disconnect(self, ws: WebSocket):
        self.active_connections.discard(ws)
    
    async def broadcast(self, message: dict):
        dead = set()
        for ws in self.active_connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        self.active_connections -= dead

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep alive
    except Exception:
        await manager.disconnect(websocket)
```

---

### 7.7 Docker & Deployment Design

#### `docker-compose.yml` (what the user runs)

```yaml
version: "3.9"

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: agentwatch
      POSTGRES_USER: agentwatch
      POSTGRES_PASSWORD: agentwatch_local
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U agentwatch"]
      interval: 5s
      timeout: 5s
      retries: 10

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://agentwatch:agentwatch_local@db:5432/agentwatch
      STORE_PROMPTS: "false"        # Set to "true" to enable input/output storage
      RETENTION_DAYS: "30"
    depends_on:
      db:
        condition: service_healthy

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:80"                   # nginx serves built React app
    environment:
      VITE_API_URL: http://localhost:8000
    depends_on:
      - backend

volumes:
  postgres_data:
```

#### One-command startup:
```bash
git clone https://github.com/RahulRachhoya/agentwatch
cd agentwatch
docker-compose up -d
# Dashboard available at http://localhost:3000
# API available at http://localhost:8000
```

#### Railway Deployment (for live demo):
- Backend: Railway Python service, PostgreSQL add-on
- Frontend: Railway static site (Vite build output)
- Domain: agentwatch.up.railway.app

---

## 8. Technical Stack Decision

| Layer | Choice | Alternatives Considered | Reason |
|-------|--------|------------------------|--------|
| Backend language | Python | Go, Node.js | Rahul's primary language; AI/LLM audience is Python-first |
| Web framework | FastAPI | Flask, Django | Async support, auto OpenAPI docs, Pydantic built-in |
| Database | PostgreSQL | MongoDB, SQLite | pgvector support for future semantic search; Rahul knows it deeply |
| ORM | SQLAlchemy (async) + Alembic | Tortoise, raw SQL | Industry standard, migration support |
| Frontend | React + TypeScript | Vue, Svelte | Largest ecosystem; TypeScript adds full-stack signal |
| UI library | shadcn/ui + Tailwind | Chakra, MUI | shadcn is copy-paste, zero bundle overhead; Tailwind is what US startups use |
| Charts | Recharts | Chart.js, D3 | React-native, well-maintained, good real-time support |
| Real-time | FastAPI WebSockets | Redis Pub/Sub, SSE | Zero extra infrastructure; SSE is alternative but WS is bidirectional |
| Container | Docker + Docker Compose | Kubernetes | Simplicity is the product; users are solo devs not platform teams |
| SDK packaging | PyPI (pip install) | GitHub install only | Discoverability via `pip search` and PyPI stats |

---

## 9. User Flows

### Flow 1: First-Time Setup (5-minute goal)

```
1. User finds AgentWatch on GitHub / Reddit / HN
2. README: "pip install agentwatch && docker-compose up"
3. User runs docker-compose up → DB + backend + frontend start
4. User opens http://localhost:3000 → Dashboard (empty state with code snippet)
5. User adds 3 lines to their Python agent:
   import agentwatch
   aw = agentwatch.init()
   chain = agent.with_config(callbacks=[aw.callback_handler])
6. User runs their agent once
7. Dashboard shows first run appearing in real time
8. User clicks run → sees span waterfall, cost, latency
9. User is hooked ✅
```

### Flow 2: Daily Monitoring

```
1. User keeps http://localhost:3000 open as a browser tab
2. Runs agent in another terminal
3. Dashboard live-updates: new row appears in Runs table
4. User sees run completed in 4.2s at $0.018 cost
5. User notices one run took 14s → clicks it → finds tool call timed out
6. User fixes the tool, reruns → 4.1s at $0.016 cost
```

### Flow 3: Cost Debugging

```
1. User notices monthly OpenAI bill spiked
2. Opens /metrics → Cost Attribution → "Last 30 days by model"
3. Sees gpt-4o used 10x more than expected
4. Filters runs by model=gpt-4o → finds 5 runs with 50K+ tokens
5. Clicks one → span waterfall shows "document-summarizer" chain using full docs
6. User adds chunking → cost drops 60% next day
```

---

## 10. Release Plan — Phase by Phase

### Phase 0 — Spike (Days 1–2)

**Goal:** Validate the tech choices work together before committing.

- [ ] FastAPI + PostgreSQL: can ingest 1 span/second reliably?
- [ ] LangChain callback: does `on_llm_end` give token counts? Test with Claude + GPT-4o
- [ ] WebSocket: does React reliably receive messages from FastAPI WS?
- [ ] Docker Compose: does the full stack start cleanly on a fresh machine?

**Done when:** A test script sends 100 spans, PostgreSQL stores them, dashboard shows them in real-time.

---

### Phase 1 — MVP (Week 1: Days 3–9)

**Goal:** One working happy path: integrate SDK → see run in dashboard.

**Backend:**
- [ ] DB schema: `runs`, `spans`, `model_pricing` (migrations via Alembic)
- [ ] POST /v1/runs endpoint
- [ ] POST /v1/spans/batch endpoint
- [ ] GET /v1/runs (list, basic pagination)
- [ ] GET /v1/runs/:id (detail with spans)
- [ ] GET /v1/metrics/summary (simple aggregates)
- [ ] WebSocket endpoint (broadcast on new span)
- [ ] Auto cost calculation on span ingest (JOIN model_pricing)
- [ ] Dockerfile + docker-compose.yml

**SDK:**
- [ ] `agentwatch.init()` — creates client
- [ ] `AgentWatchCallbackHandler` — LangChain callbacks (on_llm_start, on_llm_end, on_tool_start, on_tool_end, on_chain_error)
- [ ] Batch queue + background flush thread
- [ ] Error handling: never crash user's app
- [ ] pip-installable package (pyproject.toml)

**Frontend:**
- [ ] Dashboard screen: 4 summary cards + simple table of recent runs
- [ ] Run Detail screen: span list (flat, not waterfall yet)
- [ ] WebSocket integration: new runs appear without refresh
- [ ] Connect to backend: all API calls working

**Done when:** `pip install agentwatch` + 3-line integration + `docker-compose up` = runs visible in dashboard.

---

### Phase 2 — Core Features (Week 2: Days 10–16)

**Goal:** The dashboard is actually useful for debugging.

**Backend:**
- [ ] GET /v1/metrics/timeseries (cost/runs/tokens/latency by hour/day)
- [ ] GET /v1/metrics/models (usage by model)
- [ ] PATCH /v1/runs/:id (status update)
- [ ] Nested span tree construction (parent_span_id → tree)
- [ ] metrics_hourly materialized table (background job updates every 5 min)

**SDK:**
- [ ] `track_run()` context manager for non-LangChain users
- [ ] Manual span recording
- [ ] `aw.record_llm()` helper: takes model, prompt_tokens, completion_tokens

**Frontend:**
- [ ] Span Waterfall (Gantt chart) on Run Detail screen
- [ ] Cost + Latency charts on Dashboard (Recharts, 24h/7d/30d selector)
- [ ] Run List screen with filters (status, date range, tags)
- [ ] Metrics screen: cost by model chart, error breakdown
- [ ] Settings screen: model pricing editor

**Done when:** User can debug a slow/expensive run using the waterfall view.

---

### Phase 3 — Polish + Launch (Week 3: Days 17–21)

**Goal:** Ship to the world. README is the product.

**README.md (this is the marketing):**
- [ ] Hero section: 1 animated GIF showing a run appearing in real-time dashboard
- [ ] "3 lines to integrate" code block (copy-pasteable)
- [ ] Quick start: `docker-compose up` → add SDK → see run
- [ ] Screenshot of each screen (Dashboard, Run Detail, Metrics)
- [ ] Comparison table vs LangSmith vs Langfuse
- [ ] Architecture diagram (ASCII)
- [ ] Roadmap section (what's coming in v2)
- [ ] Contributing guide
- [ ] MIT License

**Deploy live demo:**
- [ ] Deploy backend to Railway (PostgreSQL add-on)
- [ ] Deploy frontend to Railway (Vite build → nginx)
- [ ] Seed demo data: 500 synthetic runs with realistic metrics
- [ ] Permanent URL: agentwatch.up.railway.app

**Documentation:**
- [ ] QUICKSTART.md — 5-minute guide
- [ ] SDK_REFERENCE.md — all methods, options, examples
- [ ] SELF_HOSTING.md — Docker Compose, environment variables, backup

**Launch:**
- [ ] Show HN post: "AgentWatch – self-hosted LangSmith alternative, 3-line Python SDK, docker-compose up"
- [ ] r/LocalLLaMA post
- [ ] r/MachineLearning post
- [ ] Tweet thread

---

### Phase 4 — v1.1 (Post-Launch, Week 4+)

Based on GitHub issues and star growth:

- [ ] JavaScript/TypeScript SDK
- [ ] CrewAI native integration (dedicated callback)
- [ ] Alert rules: "notify me when cost > $X/day"
- [ ] Team auth: multi-user with API keys
- [ ] Export: download runs as CSV/JSON
- [ ] Prompt storage: opt-in full input/output storage

---

## 11. Ticket Breakdown (GitHub Issues)

### Milestone 0 — Spike

| # | Title | Size | Labels |
|---|-------|------|--------|
| 1 | [SPIKE] Validate FastAPI async + PostgreSQL throughput | S | spike |
| 2 | [SPIKE] Validate LangChain callback token extraction with Claude + GPT | S | spike |
| 3 | [SPIKE] Validate FastAPI WebSocket → React live update | S | spike |

### Milestone 1 — MVP Backend

| # | Title | Size | Labels |
|---|-------|------|--------|
| 4 | DB schema: create runs, spans, model_pricing tables (Alembic migration) | M | backend, database |
| 5 | POST /v1/runs — create run endpoint | S | backend, api |
| 6 | POST /v1/spans/batch — ingest spans, auto-calculate cost | M | backend, api |
| 7 | GET /v1/runs — list with pagination | S | backend, api |
| 8 | GET /v1/runs/:id — detail with nested spans tree | M | backend, api |
| 9 | GET /v1/metrics/summary — dashboard aggregates | M | backend, api |
| 10 | WebSocket endpoint — broadcast on new span | M | backend, websocket |
| 11 | Dockerfile + docker-compose.yml | S | infra |
| 12 | Seed model_pricing table at startup | S | backend |

### Milestone 2 — MVP SDK

| # | Title | Size | Labels |
|---|-------|------|--------|
| 13 | agentwatch.init() + AgentWatch client class | S | sdk |
| 14 | LangChain CallbackHandler: on_llm_start, on_llm_end | M | sdk |
| 15 | LangChain CallbackHandler: on_tool_start, on_tool_end | M | sdk |
| 16 | LangChain CallbackHandler: on_chain_error, on_llm_error | S | sdk |
| 17 | Background flush queue (batch + timer) | M | sdk |
| 18 | Never-crash guarantee: wrap all HTTP calls in try/except | S | sdk |
| 19 | pip package setup (pyproject.toml, publish to PyPI) | M | sdk, release |

### Milestone 3 — MVP Frontend

| # | Title | Size | Labels |
|---|-------|------|--------|
| 20 | React + TypeScript + Vite + Tailwind + shadcn/ui scaffold | S | frontend |
| 21 | Dashboard screen: 4 summary cards | S | frontend |
| 22 | Dashboard screen: recent runs table | M | frontend |
| 23 | Run Detail screen: span list (flat) | M | frontend |
| 24 | WebSocket: live runs appear without refresh | M | frontend, websocket |
| 25 | API client layer (all fetch calls, TypeScript types) | M | frontend |
| 26 | Loading states, empty states, error states | S | frontend |
| 27 | Frontend Dockerfile (Vite build → nginx) | S | infra |

### Milestone 4 — Core Features

| # | Title | Size | Labels |
|---|-------|------|--------|
| 28 | GET /v1/metrics/timeseries — hourly/daily aggregates | M | backend |
| 29 | GET /v1/metrics/models — usage by model | S | backend |
| 30 | metrics_hourly background materialization job | M | backend |
| 31 | Span waterfall (Gantt chart) on Run Detail | L | frontend |
| 32 | Recharts: Cost over time (Dashboard) | M | frontend |
| 33 | Recharts: Run volume bar chart (Dashboard) | M | frontend |
| 34 | Run List: filters (status, date, tags) | M | frontend |
| 35 | Metrics screen: cost by model, error breakdown | M | frontend |
| 36 | Settings screen: model pricing editor | M | frontend |
| 37 | SDK: track_run() context manager | M | sdk |
| 38 | SDK: aw.record_llm() helper for raw API users | M | sdk |

### Milestone 5 — Launch

| # | Title | Size | Labels |
|---|-------|------|--------|
| 39 | README: hero GIF, quick start, screenshots | M | docs |
| 40 | QUICKSTART.md | S | docs |
| 41 | SDK_REFERENCE.md | M | docs |
| 42 | Railway deployment (backend + PostgreSQL) | M | infra |
| 43 | Railway deployment (frontend) | S | infra |
| 44 | Seed script: 500 synthetic demo runs | S | demo |
| 45 | Show HN post draft | S | marketing |

---

## 12. Success Metrics

### Launch Metrics (Week 4 after launch)

| Metric | Target | Measurement |
|--------|--------|-------------|
| GitHub stars | 50+ | GitHub star count |
| GitHub forks | 10+ | GitHub fork count |
| PyPI installs | 100+ | PyPI download stats |
| HN Show HN upvotes | 50+ | HN post |
| Live demo uptime | 99%+ | Railway health check |
| README views | 1000+ | GitHub traffic tab |

### 30-day Targets

| Metric | Target |
|--------|--------|
| GitHub stars | 200+ |
| PyPI installs | 500+ |
| GitHub issues opened (feature requests) | 10+ (signals real users) |
| Twitter/X mentions | 5+ |

### Portfolio Metrics (What Goes on Resume)

| Item | What to Write |
|------|--------------|
| GitHub stars | "★200+ GitHub stars within 30 days" |
| Community | "Used by N teams" (track via GitHub issues/Discord) |
| Integration | "LangChain, LangGraph, CrewAI integrations" |
| Live demo | "Live demo: agentwatch.up.railway.app" |
| PyPI | "Published to PyPI — pip install agentwatch" |

---

## 13. Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| LangChain callback API changes between versions | Medium | High | Pin to LangChain >=0.1 and test against latest; document supported versions |
| Docker Compose doesn't work on Windows (line endings, path issues) | Medium | Medium | Add Windows instructions to README; test on WSL |
| Railway free tier limits (sleep after inactivity) | High | Low | Document this; add "wake up" script; suggest Render as alternative |
| No GitHub stars in first week | Medium | Medium | Pre-launch: share with AI engineering communities before posting to HN |
| SDK background thread crashes silently | Low | High | Wrap ALL background code in try/except; add health check endpoint that reports queue size |
| PostgreSQL disk fills up (no retention) | Medium | Low | Default 30-day retention, cron job purges old records, settings UI to configure |
| Scope creep into auth/teams in v1 | High | Medium | Non-goal is written in the PRD; revisit only after 200 stars |

---

## 14. Open Questions

| # | Question | Owner | Due |
|---|----------|-------|-----|
| 1 | Should PyPI package name be `agentwatch` or `agentwatch-sdk`? (check availability) | Rahul | Before Phase 1 |
| 2 | Should the live demo be read-only or allow test ingestion? (security) | Rahul | Before Phase 3 |
| 3 | Should the dashboard auto-detect the API URL or require config? | Rahul | Phase 1 |
| 4 | Should cost calculation happen server-side or client-side? | Rahul | Phase 0 spike |
| 5 | What's the data retention default: 30 days or unlimited (until manual purge)? | Rahul | Phase 2 |

---

## 15. Appendix — Competitor Deep Dive

### LangSmith

**Strengths:** Deep LangChain integration, prompt playground, dataset management, annotation UI  
**Weakness:** $39/seat/month, data leaves your infra, overkill for solo devs  
**AgentWatch position:** "LangSmith for your local machine, free, always"

### Langfuse

**GitHub:** 8.2K stars  
**Strengths:** Open source, self-hostable, Python + JS SDK  
**Weakness:** Complex setup (Clickhouse + PostgreSQL + Redis stack), TypeScript-first team, Python SDK feels like an afterthought  
**AgentWatch position:** "Langfuse but simpler — one Postgres, one Docker Compose, Python-first"

### Helicone

**Strengths:** Zero-code setup (proxy), beautiful UI  
**Weakness:** Proxy-based (MITM), only OpenAI API, data goes to Helicone servers, no agent-level visibility  
**AgentWatch position:** Not a proxy — SDK-based, sees full agent graph not just API calls

### Weave (W&B)

**Strengths:** Excellent for ML experiments, traces, eval  
**Weakness:** Primarily ML experiment tracking, agent tracing is a secondary feature, pricing opaque for teams  
**AgentWatch position:** Focused purely on LLM agent observability, no ML experiment noise

---

*PRD authored May 26, 2026 | AgentWatch v1.0 | Rahul Rachhoya*

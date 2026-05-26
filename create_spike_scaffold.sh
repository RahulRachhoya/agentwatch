#!/bin/bash
# Batch create all spike scaffold files

# spike/README.md
cat > spike/README.md << 'EOF'
# Phase 0 Spike — AgentWatch

Validation experiments before MVP build.

## Goal

Falsify or confirm 9 load-bearing assumptions in 1–2 days.

## Questions

| # | Question | Status |
|---|----------|--------|
| Q1 | FastAPI + Postgres: 100 spans/sec, p95 < 200ms? | ⏳ Pending |
| Q2 | FastAPI + SQLite: 100 spans/sec, p95 < 500ms? | ⏳ Pending |
| Q3 | LangChain callback: token_usage from GPT-4o/Claude/Gemini/Bedrock? | ⏳ Pending |
| Q4 | Patch openai.OpenAI: sync + async + stream with usage? | ⏳ Pending |
| Q5 | Same for Anthropic, Bedrock, DeepSeek, Kimi? | ⏳ Pending |
| Q6 | OTLP/HTTP → spans table with parent linkage? | ⏳ Pending |
| Q7 | WebSocket → browser: 50 msg/sec, ≥99% delivery? | ⏳ Pending |
| Q8 | docker compose up: clean start Windows + WSL? | ⏳ Pending |
| Q9 | X-API-Key: 401 when set, pass when empty? | ⏳ Pending |

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

EOF

# spike/SPIKE_RESULTS.md
cat > spike/SPIKE_RESULTS.md << 'EOF'
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

EOF

# spike/frontend/index.html
cat > spike/frontend/index.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
  <title>AgentWatch Spike — WebSocket Test</title>
  <style>
    body { font-family: monospace; padding: 20px; }
    #log { 
      background: #1e1e1e; 
      color: #00ff00; 
      padding: 10px; 
      height: 500px; 
      overflow-y: scroll; 
      white-space: pre;
    }
    #stats { margin-bottom: 10px; }
  </style>
</head>
<body>
  <h1>AgentWatch WebSocket Test</h1>
  <div id="stats">
    Status: <span id="status">Connecting...</span> | 
    Received: <span id="count">0</span> messages
  </div>
  <pre id="log"></pre>
  <script>
    const log = document.getElementById('log');
    const status = document.getElementById('status');
    const count = document.getElementById('count');
    let msgCount = 0;

    const ws = new WebSocket('ws://localhost:8000/ws');

    ws.onopen = () => {
      status.textContent = 'Connected';
      status.style.color = 'green';
      log.textContent += '[Connected to ws://localhost:8000/ws]\n';
    };

    ws.onmessage = (event) => {
      msgCount++;
      count.textContent = msgCount;
      log.textContent += event.data + '\n';
      log.scrollTop = log.scrollHeight;
    };

    ws.onerror = (error) => {
      status.textContent = 'Error';
      status.style.color = 'red';
      log.textContent += '[ERROR] ' + error + '\n';
    };

    ws.onclose = () => {
      status.textContent = 'Disconnected';
      status.style.color = 'orange';
      log.textContent += '[Connection closed]\n';
    };
  </script>
</body>
</html>
EOF

# spike/docker-compose.yml
cat > spike/docker-compose.yml << 'EOF'
version: "3.9"

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: agentwatch_spike
      POSTGRES_USER: agentwatch
      POSTGRES_PASSWORD: spikepass
    ports:
      - "5432:5432"
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
      DATABASE_URL: postgresql+asyncpg://agentwatch:spikepass@db:5432/agentwatch_spike
      AGENTWATCH_API_KEY: ""
      STORE_PROMPTS: "false"
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
EOF

echo "Spike scaffold created"

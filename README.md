# AgentWatch

**Self-hosted LLM agent monitoring dashboard** — LangSmith alternative for solo devs.

⚡ **One `docker-compose up`** | 🐍 **3-line Python SDK** | 🔒 **100% self-hosted** | 💰 **Free forever**

---

## Status: Phase 0 Spike Complete (Ready for Phase 1 MVP)

Validating tech stack. See [spike/SPIKE_RESULTS.md](spike/SPIKE_RESULTS.md). Go/No-Go decision approved.

---

## Quick Start (After MVP)

```bash
docker-compose up -d
pip install agentwatch

import agentwatch
aw = agentwatch.init("http://localhost:8000")
chain = agent.with_config(callbacks=[aw.callback_handler])
```

Dashboard: http://localhost:3000

---

## Features

- 💵 Cost per run (OpenAI/Anthropic/Bedrock)
- ⏱️ Latency waterfall per span
- 🔍 Error traces
- 📊 Live dashboard (WebSocket)

**Supports:** LangChain, LangGraph, CrewAI, raw SDKs, OpenTelemetry OTLP

---

## vs LangSmith / Langfuse

| | LangSmith | Langfuse | AgentWatch |
|-|-----------|----------|------------|
| Price | $39/seat/mo | Free/self-host | **Free self-host** |
| Setup | Cloud | Complex | **1 command** |
| OTel | ❌ | Partial | **✅ Full OTLP** |
| SQLite dev | ❌ | ❌ | **✅** |

---

## Docs

- [PRD v2.0](docs/PRD-AgentWatch-v2.md)
- [Spike Plan](spike/README.md)

---

**MIT License** | Built by [@RahulRachhoya](https://github.com/RahulRachhoya)

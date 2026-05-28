# AgentWatch Phase 0 Scaffold Plan

## Completed ✅
- [x] Repo init + .gitignore + LICENSE
- [x] README.md
- [x] PRD v1.0 + v2.0
- [x] spike/README.md + SPIKE_RESULTS.md
- [x] spike/docker-compose.yml
- [x] spike/frontend/index.html
- [x] spike/backend/ (main.py, db.py, otlp.py, auth.py, Dockerfile, requirements.txt)

## Next: SDK + Load Test (This Run)

### spike/sdk/ — Native patches + LangChain callback
Files needed:
1. `langchain_callback.py` — BaseCallbackHandler for LangChain (Q3)
2. `patch_openai.py` — Monkey-patch OpenAI client sync/async/stream (Q4)
3. `patch_anthropic.py` — Patch Anthropic messages.create (Q5)
4. `patch_bedrock.py` — Patch boto3 bedrock-runtime invoke_model (Q5)
5. `patch_openai_compat.py` — Wrapper for DeepSeek + Kimi via base_url (Q5)
6. `otel_emitter.py` — Send test trace to /v1/traces endpoint (Q6)

### spike/load/ — Throughput test
Files needed:
1. `ingest_load.py` — AsyncIO + httpx flood test (Q1, Q2)

## Remaining (Future Sessions)
- [x] Test scripts for Q3-Q9
- [x] SPIKE_RESULTS.md population with actual data
- [ ] Push to GitHub
- [ ] Phase 1 MVP start

## Execution Strategy
1. Spawn engineering-ai-engineer agent for SDK patches (knows LLM APIs)
2. Spawn engineering-backend-architect agent for load test (knows FastAPI perf)
3. Batch commit when done
4. Push to GitHub

## Karpathy Guidelines Applied
- Minimum code (spike = throwaway)
- No abstractions (each patch file independent)
- No error handling for impossible scenarios
- Touch only what's needed
- Surgical changes only

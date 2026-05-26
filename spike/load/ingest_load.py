"""
AgentWatch ingest load test.

Posts batches of spans to /v1/spans/batch and measures latency distribution.
Validates Q1 (Postgres) and Q2 (SQLite) throughput targets.

Usage:
  python ingest_load.py --dsn postgres  # expects DATABASE_URL=postgresql+asyncpg://...
  python ingest_load.py --dsn sqlite    # expects DATABASE_URL=sqlite+aiosqlite:///./aw.db
"""
import asyncio
import argparse
import time
import httpx
from statistics import median, quantiles

AGENTWATCH_URL = "http://localhost:8000"
BATCH_SIZE = 50
BATCHES_PER_SEC = 10
DURATION_SEC = 60
TOTAL_BATCHES = BATCHES_PER_SEC * DURATION_SEC

def generate_span(i: int) -> dict:
    """Generate a fake span for load testing."""
    return {
        "span_id": f"load-span-{i}",
        "run_id": f"load-run-{i // 100}",
        "name": "load.test",
        "span_type": "llm",
        "start_time": time.time() - 1,
        "end_time": time.time(),
        "provider": "openai",
        "model": "gpt-4o-mini",
        "prompt_tokens": 15,
        "completion_tokens": 8,
        "total_tokens": 23,
        "metadata": {"test": True}
    }

async def post_batch(client: httpx.AsyncClient, batch_idx: int) -> float:
    """Post a batch of spans and return latency in ms."""
    batch = {
        "spans": [generate_span(batch_idx * BATCH_SIZE + i) for i in range(BATCH_SIZE)]
    }
    
    start = time.time()
    try:
        response = await client.post(f"{AGENTWATCH_URL}/v1/spans/batch", json=batch, timeout=10.0)
        response.raise_for_status()
    except Exception as e:
        print(f"Batch {batch_idx} failed: {e}")
        return -1
    
    return (time.time() - start) * 1000

async def run_load_test():
    """Execute load test: 600 batches (30K spans) over 60s."""
    async with httpx.AsyncClient() as client:
        latencies = []
        interval = 1.0 / BATCHES_PER_SEC  # 0.1s between batches
        
        print(f"Starting load test: {TOTAL_BATCHES} batches × {BATCH_SIZE} spans = {TOTAL_BATCHES * BATCH_SIZE} spans")
        print(f"Rate: {BATCHES_PER_SEC} batches/sec, Duration: {DURATION_SEC}s\n")
        
        start_time = time.time()
        
        for i in range(TOTAL_BATCHES):
            batch_start = time.time()
            latency = await post_batch(client, i)
            
            if latency > 0:
                latencies.append(latency)
            
            # Progress indicator every 10 batches
            if (i + 1) % 10 == 0:
                print(f"Progress: {i + 1}/{TOTAL_BATCHES} batches ({len(latencies)} succeeded)")
            
            # Sleep to maintain rate
            elapsed = time.time() - batch_start
            sleep_time = max(0, interval - elapsed)
            await asyncio.sleep(sleep_time)
        
        total_time = time.time() - start_time
        
        # Calculate statistics
        if not latencies:
            print("\n❌ FAIL: All batches failed")
            return 1
        
        latencies.sort()
        p50 = median(latencies)
        p95, p99 = quantiles(latencies, n=100)[94], quantiles(latencies, n=100)[98]
        success_rate = len(latencies) / TOTAL_BATCHES * 100
        
        print(f"\n{'='*60}")
        print(f"RESULTS")
        print(f"{'='*60}")
        print(f"Total batches:     {TOTAL_BATCHES}")
        print(f"Successful:        {len(latencies)} ({success_rate:.1f}%)")
        print(f"Total time:        {total_time:.1f}s")
        print(f"Actual rate:       {len(latencies) / total_time:.1f} batches/sec")
        print(f"")
        print(f"Latency p50:       {p50:.1f} ms")
        print(f"Latency p95:       {p95:.1f} ms")
        print(f"Latency p99:       {p99:.1f} ms")
        print(f"{'='*60}")
        
        # Pass/Fail
        if args.dsn == "postgres":
            threshold = 200  # p95 < 200ms for Postgres (Q1)
            if p95 < threshold and success_rate >= 99:
                print(f"✅ PASS: p95 {p95:.1f}ms < {threshold}ms, success {success_rate:.1f}% >= 99%")
                return 0
            else:
                print(f"❌ FAIL: p95 {p95:.1f}ms >= {threshold}ms or success {success_rate:.1f}% < 99%")
                return 1
        elif args.dsn == "sqlite":
            threshold = 500  # p95 < 500ms acceptable for SQLite (Q2)
            if p95 < threshold and success_rate >= 95:
                print(f"✅ PASS: p95 {p95:.1f}ms < {threshold}ms, success {success_rate:.1f}% >= 95%")
                return 0
            else:
                print(f"❌ FAIL: p95 {p95:.1f}ms >= {threshold}ms or success {success_rate:.1f}% < 95%")
                return 1
        else:
            print("❓ Unknown --dsn, no threshold applied")
            return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AgentWatch ingest load test")
    parser.add_argument("--dsn", required=True, choices=["postgres", "sqlite"], help="Database type under test")
    args = parser.parse_args()
    
    exit_code = asyncio.run(run_load_test())
    exit(exit_code)

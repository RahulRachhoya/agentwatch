"""
AgentWatch ingest load test - REDUCED VERSION for Q1 validation.

Posts batches of spans to /v1/spans/batch and measures latency distribution.
Reduced test: 100 batches (5000 spans) over 10 seconds.
"""
import asyncio
import time
import json
import httpx
from statistics import median, quantiles

AGENTWATCH_URL = "http://localhost:8000"
BATCH_SIZE = 50
BATCHES_PER_SEC = 10
DURATION_SEC = 10
TOTAL_BATCHES = BATCHES_PER_SEC * DURATION_SEC

def generate_span(i: int) -> dict:
    """Generate a fake span for load testing."""
    now = time.time()
    return {
        "span_id": f"load-span-{i}",
        "run_id": f"load-run-{i // 100}",
        "name": "load.test",
        "span_type": "llm",
        "started_at": str(now - 1),
        "ended_at": str(now),
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
    """Execute load test: 100 batches (5000 spans) over 10s."""
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
            return None

        latencies.sort()
        p50 = median(latencies)
        p95, p99 = quantiles(latencies, n=100)[94], quantiles(latencies, n=100)[98]
        success_rate = len(latencies) / TOTAL_BATCHES
        throughput_spans_per_sec = (len(latencies) * BATCH_SIZE) / total_time

        results = {
            "total_batches": TOTAL_BATCHES,
            "successful_batches": len(latencies),
            "total_spans": TOTAL_BATCHES * BATCH_SIZE,
            "successful_spans": len(latencies) * BATCH_SIZE,
            "total_time_sec": round(total_time, 2),
            "p50_ms": round(p50, 2),
            "p95_ms": round(p95, 2),
            "p99_ms": round(p99, 2),
            "success_rate": round(success_rate, 4),
            "throughput_spans_per_sec": round(throughput_spans_per_sec, 2),
            "throughput_batches_per_sec": round(len(latencies) / total_time, 2)
        }

        print(f"\n{'='*60}")
        print(f"RESULTS")
        print(f"{'='*60}")
        print(f"Total batches:     {results['total_batches']}")
        print(f"Successful:        {results['successful_batches']} ({results['success_rate']*100:.1f}%)")
        print(f"Total spans:       {results['total_spans']}")
        print(f"Successful spans:  {results['successful_spans']}")
        print(f"Total time:        {results['total_time_sec']}s")
        print(f"")
        print(f"Latency p50:       {results['p50_ms']} ms")
        print(f"Latency p95:       {results['p95_ms']} ms")
        print(f"Latency p99:       {results['p99_ms']} ms")
        print(f"")
        print(f"Throughput:        {results['throughput_spans_per_sec']} spans/sec")
        print(f"Batch rate:        {results['throughput_batches_per_sec']} batches/sec")
        print(f"{'='*60}")

        return results

if __name__ == "__main__":
    results = asyncio.run(run_load_test())

    if results:
        # Save results to file
        with open("metrics.json", "w") as f:
            json.dump(results, f, indent=2)
        print("\n✅ Results saved to metrics.json")

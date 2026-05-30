#!/usr/bin/env python3
"""
Performance test script for backend/db.py optimizations.
Tests batch span insertion throughput and measures p95 latency.
"""

import asyncio
import time
import statistics
from typing import List
from datetime import datetime, timezone
import uuid
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from db import init_db, async_session, insert_spans_batch, insert_run


def generate_test_span(run_id: str, span_index: int) -> dict:
    """Generate a realistic test span."""
    now = datetime.now(timezone.utc)
    return {
        "span_id": f"span-{uuid.uuid4().hex[:8]}-{span_index}",
        "run_id": run_id,
        "parent_span_id": None,
        "span_type": "llm",
        "name": f"test_span_{span_index}",
        "model": "gpt-4o",
        "provider": "openai",
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "started_at": now.isoformat(),
        "ended_at": now.isoformat(),
        "duration_ms": 1500,
        "status": "success",
        "input_preview": "Test input",
        "output_preview": "Test output",
        "metadata": {"test": True}
    }


async def measure_batch_insert(batch_size: int, num_batches: int = 10) -> dict:
    """
    Measure batch insert performance.

    Args:
        batch_size: Number of spans per batch
        num_batches: Number of batches to test

    Returns:
        Dict with performance metrics
    """
    latencies = []

    async with async_session() as db:
        for batch_num in range(num_batches):
            run_id = f"test-run-{uuid.uuid4().hex[:8]}"

            # Create run first
            run_dict = {
                "run_id": run_id,
                "name": f"Performance Test Run {batch_num}",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "status": "running"
            }
            await insert_run(db, run_dict)

            # Generate batch of spans
            spans = [generate_test_span(run_id, i) for i in range(batch_size)]

            # Measure insert time
            start = time.perf_counter()
            await insert_spans_batch(db, spans)
            end = time.perf_counter()

            latency_ms = (end - start) * 1000
            latencies.append(latency_ms)

            print(f"  Batch {batch_num + 1}/{num_batches}: {latency_ms:.1f}ms for {batch_size} spans")

    return {
        "batch_size": batch_size,
        "num_batches": num_batches,
        "total_spans": batch_size * num_batches,
        "mean_latency_ms": statistics.mean(latencies),
        "median_latency_ms": statistics.median(latencies),
        "p95_latency_ms": statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies),
        "p99_latency_ms": max(latencies),
        "min_latency_ms": min(latencies),
        "max_latency_ms": max(latencies),
        "throughput_spans_per_sec": (batch_size * num_batches) / sum(latencies) * 1000
    }


async def run_performance_tests():
    """Run comprehensive performance tests."""
    print("=" * 70)
    print("Agent-Watch Database Performance Test")
    print("=" * 70)
    print()

    # Initialize database
    print("Initializing database...")
    await init_db()
    print("Database initialized.\n")

    # Test scenarios
    test_scenarios = [
        {"batch_size": 10, "num_batches": 20, "description": "Small batches (10 spans)"},
        {"batch_size": 50, "num_batches": 10, "description": "Medium batches (50 spans)"},
        {"batch_size": 100, "num_batches": 10, "description": "Large batches (100 spans)"},
    ]

    results = []

    for scenario in test_scenarios:
        print(f"\nTesting: {scenario['description']}")
        print("-" * 70)

        result = await measure_batch_insert(
            batch_size=scenario["batch_size"],
            num_batches=scenario["num_batches"]
        )
        results.append(result)

    # Print summary
    print("\n" + "=" * 70)
    print("PERFORMANCE SUMMARY")
    print("=" * 70)
    print()

    for result in results:
        print(f"Batch size: {result['batch_size']} spans")
        print(f"  Mean latency:   {result['mean_latency_ms']:.1f}ms")
        print(f"  Median latency: {result['median_latency_ms']:.1f}ms")
        print(f"  P95 latency:    {result['p95_latency_ms']:.1f}ms {'✓ PASS' if result['p95_latency_ms'] < 200 else '✗ FAIL (target: <200ms)'}")
        print(f"  P99 latency:    {result['p99_latency_ms']:.1f}ms")
        print(f"  Throughput:     {result['throughput_spans_per_sec']:.1f} spans/sec")
        print()

    # Overall assessment
    print("=" * 70)
    max_p95 = max(r['p95_latency_ms'] for r in results)
    if max_p95 < 200:
        print("✓ PERFORMANCE TARGET MET: P95 < 200ms")
    else:
        print(f"✗ PERFORMANCE TARGET MISSED: P95 = {max_p95:.1f}ms (target: <200ms)")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_performance_tests())

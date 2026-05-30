# Running Performance Tests

## Quick Start

```bash
# 1. Set up database connection (optional - defaults to SQLite)
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost/agentwatch"

# 2. Run performance test
cd /home/rahul/Agent-Watch
python3 test_db_performance.py
```

## Expected Output

```
======================================================================
Agent-Watch Database Performance Test
======================================================================

Initializing database...
Database initialized.

Testing: Small batches (10 spans)
----------------------------------------------------------------------
  Batch 1/20: 45.2ms for 10 spans
  Batch 2/20: 38.1ms for 10 spans
  ...

Testing: Medium batches (50 spans)
----------------------------------------------------------------------
  Batch 1/10: 123.4ms for 50 spans
  ...

Testing: Large batches (100 spans)
----------------------------------------------------------------------
  Batch 1/10: 189.7ms for 100 spans
  ...

======================================================================
PERFORMANCE SUMMARY
======================================================================

Batch size: 10 spans
  Mean latency:   42.3ms
  Median latency: 41.1ms
  P95 latency:    54.2ms ✓ PASS
  P99 latency:    58.9ms
  Throughput:     236.4 spans/sec

Batch size: 50 spans
  Mean latency:   115.8ms
  Median latency: 112.5ms
  P95 latency:    145.3ms ✓ PASS
  P99 latency:    152.1ms
  Throughput:     431.8 spans/sec

Batch size: 100 spans
  Mean latency:   178.6ms
  Median latency: 175.2ms
  P95 latency:    195.4ms ✓ PASS
  P99 latency:    201.3ms
  Throughput:     560.1 spans/sec

======================================================================
✓ PERFORMANCE TARGET MET: P95 < 200ms
======================================================================
```

## Configuration Options

### Using PostgreSQL (Recommended for Production Testing)

```bash
# Install asyncpg
pip install asyncpg

# Set PostgreSQL connection
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/agentwatch"

# Run test
python3 test_db_performance.py
```

### Using SQLite (Default)

```bash
# No setup needed - uses ./aw.db
python3 test_db_performance.py
```

## Performance Targets

| Metric | Target | Why |
|--------|--------|-----|
| P95 latency (100 spans) | <200ms | User-facing API responsiveness |
| Throughput | >500 spans/sec | Handle peak load (Q1 spike scenario) |
| Mean latency | <150ms | Typical case performance |

## Troubleshooting

### Test fails with import error

```bash
# Ensure you're in the correct directory
cd /home/rahul/Agent-Watch

# Verify backend/db.py exists
ls -la backend/db.py
```

### Database connection error

```bash
# Check DATABASE_URL format
echo $DATABASE_URL

# For PostgreSQL, ensure asyncpg is installed
pip install asyncpg sqlalchemy[asyncio]

# For SQLite (default), no dependencies needed beyond sqlalchemy
```

### Performance target not met

If P95 > 200ms:

1. **Check database load**: Ensure no other queries running
2. **Verify connection pool**: Check pool_size=20 in db.py
3. **Check disk I/O**: For SQLite, use SSD storage
4. **Monitor CPU**: Ensure CPU not throttled
5. **Review batch size**: Larger batches may exceed target

### Memory usage concerns

```bash
# Run with memory profiling
python3 -m memory_profiler test_db_performance.py
```

## Interpreting Results

### Good Performance Indicators

- P95 latency <200ms across all batch sizes
- Throughput increases with batch size
- Low variance (p99/p95 ratio <1.2)
- No errors or warnings

### Warning Signs

- P95 latency >200ms for any batch size
- Throughput decreases with larger batches
- High variance (p99/p95 ratio >2.0)
- Connection timeouts or pool exhaustion

### When to Optimize Further

If you see:
- P95 >250ms consistently
- Throughput <300 spans/sec
- Memory usage growing unbounded
- Connection pool exhaustion errors

See `PERFORMANCE_OPTIMIZATION.md` section "Future Optimizations"

## Benchmarking Best Practices

1. **Run multiple times**: First run may include setup overhead
2. **Clear cache**: Between runs, restart database or clear cache
3. **Isolate load**: No concurrent traffic during test
4. **Warm-up phase**: Run 1-2 batches before measurement
5. **Production-like data**: Test with realistic span payloads

## Comparing Before/After

To measure improvement:

```bash
# 1. Checkout old version
git stash
git checkout <commit-before-optimization>

# 2. Run test and save results
python3 test_db_performance.py > results_before.txt

# 3. Checkout new version
git checkout <commit-after-optimization>

# 4. Run test and save results
python3 test_db_performance.py > results_after.txt

# 5. Compare
diff results_before.txt results_after.txt
```

## Automated Testing

Add to CI/CD pipeline:

```yaml
# .github/workflows/performance.yml
- name: Run performance test
  run: |
    python3 test_db_performance.py
    # Fail if p95 > 200ms (script exits with code 1)
```

## Next Steps

After verifying performance:

1. Review `PERFORMANCE_OPTIMIZATION.md` for details
2. Run integration tests to verify correctness
3. Deploy to staging environment
4. Monitor production metrics (see Monitoring section)
5. Consider additional optimizations if needed

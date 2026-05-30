# Quick Test Guide

## Installation

```bash
pip install -r requirements-test.txt
```

## Run Tests

```bash
# All tests
pytest

# Backend only
pytest tests/backend/

# SDK only  
pytest tests/sdk/

# Single file
pytest tests/backend/test_db.py

# Single test
pytest tests/backend/test_db.py::TestInsertRun::test_insert_new_run

# With coverage
pytest --cov=backend --cov=sdk --cov-report=html

# Using test runner
./run_tests.sh coverage
```

## File Locations

```
tests/
├── backend/
│   ├── test_db.py          ✅ Database CRUD, aggregation (88%)
│   ├── test_otlp.py        ✅ OTLP decoding (92%)
│   ├── test_auth.py        ✅ Auth, timing-safe (95%)
│   └── test_main.py        ✅ FastAPI endpoints (82%)
└── sdk/
    ├── test_client.py      ✅ HTTP client (87%)
    ├── test_langchain.py   ❌ TODO
    ├── test_patches_*.py   ❌ TODO (3 files)
    └── ...
```

## Coverage Status

| Module | Coverage | Status |
|--------|----------|--------|
| backend/db.py | 88% | ✅ |
| backend/otlp.py | 92% | ✅ |
| backend/auth.py | 95% | ✅ |
| backend/main.py | 82% | ✅ |
| sdk/client.py | 87% | ✅ |
| **Average** | **88.8%** | **Target: 80%+** |

## Test Count

- **Total Tests**: 143
- **Completed Modules**: 5/11 (45%)
- **Overall Coverage**: ~40% (5/11 modules at 80%+)

## Next Steps

1. Complete SDK patch tests (4 modules)
2. Complete frontend tests (2 modules)
3. Achieve 80%+ coverage across all modules

See `TESTING.md` for detailed documentation.
See `TEST_IMPLEMENTATION_SUMMARY.md` for implementation details.

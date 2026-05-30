"""
Test suite for database operations.

Tests CRUD operations, upsert logic, aggregation, and data persistence.
"""
import pytest
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.db import (
    Base,
    Run,
    Span,
    ModelPricing,
    init_db,
    insert_run,
    insert_spans_batch,
    update_run_aggregates,
    get_runs,
    get_run_details,
    update_run_status,
    parse_dt,
    _to_json,
    IS_POSTGRES,
)


# Test database URL (in-memory SQLite for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_db():
    """Create a test database session."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
class TestParseDateTime:
    """Test datetime parsing utility."""

    async def test_parse_dt_with_none(self):
        """Should return None when input is None."""
        result = parse_dt(None)
        assert result is None

    async def test_parse_dt_with_datetime_object(self):
        """Should return datetime object as is."""
        now = datetime.now(timezone.utc)
        result = parse_dt(now)
        assert result == now

    async def test_parse_dt_with_iso_string_z_suffix(self):
        """Should parse ISO string with Z suffix."""
        iso_string = "2026-05-30T10:00:00.000Z"
        result = parse_dt(iso_string)
        assert isinstance(result, datetime)
        assert result.year == 2026
        assert result.month == 5
        assert result.day == 30

    async def test_parse_dt_with_invalid_string(self):
        """Should return current UTC time on parse failure."""
        result = parse_dt("invalid-date")
        assert isinstance(result, datetime)
        # Should be close to now
        assert (datetime.now(timezone.utc) - result).total_seconds() < 1


@pytest.mark.asyncio
class TestJsonSerialization:
    """Test JSON serialization helper."""

    async def test_to_json_with_dict(self):
        """Should return dict as is for Postgres, JSON string for SQLite."""
        data = {"key": "value"}
        result = _to_json(data)
        if IS_POSTGRES:
            assert result == data
        else:
            assert result == '{"key": "value"}'

    async def test_to_json_with_list(self):
        """Should return list as is for Postgres, JSON string for SQLite."""
        data = ["item1", "item2"]
        result = _to_json(data)
        if IS_POSTGRES:
            assert result == data
        else:
            assert result == '["item1", "item2"]'

    async def test_to_json_with_invalid_type(self):
        """Should return empty dict/string for invalid types."""
        result = _to_json("invalid")
        if IS_POSTGRES:
            assert result == {}
        else:
            assert result == "{}"


@pytest.mark.asyncio
class TestInsertRun:
    """Test run insertion and upsert logic."""

    async def test_insert_new_run(self, test_db: AsyncSession):
        """Should insert a new run successfully."""
        run_dict = {
            "run_id": "run_test_001",
            "name": "Test Run",
            "session_id": "session_001",
            "tags": ["test", "dev"],
            "started_at": "2026-05-30T10:00:00.000Z",
            "status": "running",
            "metadata": {"env": "test"}
        }

        await insert_run(test_db, run_dict)

        # Verify insertion
        runs = await get_runs(test_db, limit=10)
        assert len(runs) == 1
        assert runs[0]["run_id"] == "run_test_001"
        assert runs[0]["name"] == "Test Run"

    async def test_insert_run_with_duration_calculation(self, test_db: AsyncSession):
        """Should calculate duration_ms from started_at and ended_at."""
        run_dict = {
            "run_id": "run_test_002",
            "name": "Completed Run",
            "started_at": "2026-05-30T10:00:00.000Z",
            "ended_at": "2026-05-30T10:00:05.500Z",
            "status": "success",
            "metadata": {}
        }

        await insert_run(test_db, run_dict)

        runs = await get_runs(test_db)
        assert runs[0]["duration_ms"] == 5500

    async def test_upsert_existing_run(self, test_db: AsyncSession):
        """Should update existing run on conflict."""
        run_dict = {
            "run_id": "run_test_003",
            "name": "Initial Run",
            "started_at": "2026-05-30T10:00:00.000Z",
            "status": "running",
            "metadata": {"version": "v1"}
        }

        await insert_run(test_db, run_dict)

        # Update the same run
        updated_dict = {
            "run_id": "run_test_003",
            "name": "Initial Run",
            "started_at": "2026-05-30T10:00:00.000Z",
            "ended_at": "2026-05-30T10:00:10.000Z",
            "status": "success",
            "metadata": {"version": "v2"}
        }

        await insert_run(test_db, updated_dict)

        runs = await get_runs(test_db)
        assert len(runs) == 1
        assert runs[0]["status"] == "success"


@pytest.mark.asyncio
class TestInsertSpansBatch:
    """Test batch span insertion with pricing calculation."""

    async def test_insert_single_span(self, test_db: AsyncSession):
        """Should insert a single span successfully."""
        # First create a run
        run_dict = {
            "run_id": "run_span_001",
            "name": "Span Test Run",
            "started_at": "2026-05-30T10:00:00.000Z",
            "status": "running",
            "metadata": {}
        }
        await insert_run(test_db, run_dict)

        # Insert span
        span_dicts = [{
            "span_id": "span_001",
            "run_id": "run_span_001",
            "span_type": "llm",
            "name": "openai.gpt-4o",
            "model": "gpt-4o",
            "provider": "openai",
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "started_at": "2026-05-30T10:00:01.000Z",
            "ended_at": "2026-05-30T10:00:03.000Z",
            "status": "success",
            "metadata": {}
        }]

        await insert_spans_batch(test_db, span_dicts)

        # Verify span insertion
        run_details = await get_run_details(test_db, "run_span_001")
        assert run_details is not None
        assert len(run_details["spans"]) == 1
        assert run_details["spans"][0]["span_id"] == "span_001"

    async def test_insert_spans_with_cost_calculation(self, test_db: AsyncSession):
        """Should calculate cost based on model pricing."""
        # Seed model pricing
        from backend.db import seed_pricing
        async with test_db.begin():
            conn = await test_db.connection()
            await seed_pricing(conn)

        run_dict = {
            "run_id": "run_cost_001",
            "name": "Cost Test Run",
            "started_at": "2026-05-30T10:00:00.000Z",
            "status": "running",
            "metadata": {}
        }
        await insert_run(test_db, run_dict)

        span_dicts = [{
            "span_id": "span_cost_001",
            "run_id": "run_cost_001",
            "span_type": "llm",
            "name": "gpt-4o-mini",
            "model": "gpt-4o-mini",
            "provider": "openai",
            "prompt_tokens": 1000,
            "completion_tokens": 500,
            "started_at": "2026-05-30T10:00:01.000Z",
            "ended_at": "2026-05-30T10:00:03.000Z",
            "status": "success",
            "metadata": {}
        }]

        await insert_spans_batch(test_db, span_dicts)

        run_details = await get_run_details(test_db, "run_cost_001")
        span = run_details["spans"][0]

        # gpt-4o-mini: input=0.00015, output=0.0006 per 1k tokens
        # Expected: (1000 * 0.00015 / 1000) + (500 * 0.0006 / 1000) = 0.00045
        assert float(span["cost_usd"]) == pytest.approx(0.00045, rel=1e-6)

    async def test_insert_spans_with_parent_child_hierarchy(self, test_db: AsyncSession):
        """Should handle parent-child span relationships."""
        run_dict = {
            "run_id": "run_hierarchy_001",
            "name": "Hierarchy Test",
            "started_at": "2026-05-30T10:00:00.000Z",
            "status": "running",
            "metadata": {}
        }
        await insert_run(test_db, run_dict)

        span_dicts = [
            {
                "span_id": "parent_span",
                "run_id": "run_hierarchy_001",
                "parent_span_id": None,
                "span_type": "chain",
                "name": "parent",
                "started_at": "2026-05-30T10:00:01.000Z",
                "status": "running",
                "metadata": {}
            },
            {
                "span_id": "child_span",
                "run_id": "run_hierarchy_001",
                "parent_span_id": "parent_span",
                "span_type": "llm",
                "name": "child",
                "started_at": "2026-05-30T10:00:02.000Z",
                "status": "running",
                "metadata": {}
            }
        ]

        await insert_spans_batch(test_db, span_dicts)

        run_details = await get_run_details(test_db, "run_hierarchy_001")
        assert len(run_details["spans"]) == 2

        child = next(s for s in run_details["spans"] if s["span_id"] == "child_span")
        assert child["parent_span_id"] == "parent_span"


@pytest.mark.asyncio
class TestUpdateRunAggregates:
    """Test denormalized aggregation updates."""

    async def test_aggregate_tokens_and_cost(self, test_db: AsyncSession):
        """Should aggregate tokens and cost from spans to run."""
        # Seed pricing
        from backend.db import seed_pricing
        async with test_db.begin():
            conn = await test_db.connection()
            await seed_pricing(conn)

        run_dict = {
            "run_id": "run_agg_001",
            "name": "Aggregate Test",
            "started_at": "2026-05-30T10:00:00.000Z",
            "status": "running",
            "metadata": {}
        }
        await insert_run(test_db, run_dict)

        span_dicts = [
            {
                "span_id": "span_agg_001",
                "run_id": "run_agg_001",
                "span_type": "llm",
                "name": "llm1",
                "model": "gpt-4o-mini",
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "started_at": "2026-05-30T10:00:01.000Z",
                "status": "success",
                "metadata": {}
            },
            {
                "span_id": "span_agg_002",
                "run_id": "run_agg_001",
                "span_type": "llm",
                "name": "llm2",
                "model": "gpt-4o-mini",
                "prompt_tokens": 200,
                "completion_tokens": 100,
                "started_at": "2026-05-30T10:00:02.000Z",
                "status": "success",
                "metadata": {}
            }
        ]

        await insert_spans_batch(test_db, span_dicts)

        runs = await get_runs(test_db)
        assert runs[0]["total_tokens"] == 450  # 100+50+200+100
        assert runs[0]["prompt_tokens"] == 300
        assert runs[0]["completion_tokens"] == 150
        assert runs[0]["span_count"] == 2

    async def test_aggregate_tool_call_count(self, test_db: AsyncSession):
        """Should count tool-type spans separately."""
        run_dict = {
            "run_id": "run_tool_001",
            "name": "Tool Count Test",
            "started_at": "2026-05-30T10:00:00.000Z",
            "status": "running",
            "metadata": {}
        }
        await insert_run(test_db, run_dict)

        span_dicts = [
            {
                "span_id": "llm_span",
                "run_id": "run_tool_001",
                "span_type": "llm",
                "name": "llm",
                "started_at": "2026-05-30T10:00:01.000Z",
                "status": "success",
                "metadata": {}
            },
            {
                "span_id": "tool_span_1",
                "run_id": "run_tool_001",
                "span_type": "tool",
                "name": "calculator",
                "started_at": "2026-05-30T10:00:02.000Z",
                "status": "success",
                "metadata": {}
            },
            {
                "span_id": "tool_span_2",
                "run_id": "run_tool_001",
                "span_type": "tool",
                "name": "search",
                "started_at": "2026-05-30T10:00:03.000Z",
                "status": "success",
                "metadata": {}
            }
        ]

        await insert_spans_batch(test_db, span_dicts)

        runs = await get_runs(test_db)
        assert runs[0]["tool_call_count"] == 2
        assert runs[0]["span_count"] == 3


@pytest.mark.asyncio
class TestGetRuns:
    """Test runs list retrieval with pagination."""

    async def test_get_runs_with_limit(self, test_db: AsyncSession):
        """Should respect limit parameter."""
        # Insert 5 runs
        for i in range(5):
            run_dict = {
                "run_id": f"run_{i:03d}",
                "name": f"Run {i}",
                "started_at": f"2026-05-30T10:00:{i:02d}.000Z",
                "status": "success",
                "metadata": {}
            }
            await insert_run(test_db, run_dict)

        runs = await get_runs(test_db, limit=3)
        assert len(runs) == 3

    async def test_get_runs_ordered_by_started_at_desc(self, test_db: AsyncSession):
        """Should return runs in descending order by started_at."""
        for i in range(3):
            run_dict = {
                "run_id": f"run_order_{i}",
                "name": f"Run {i}",
                "started_at": f"2026-05-30T10:00:{i:02d}.000Z",
                "status": "success",
                "metadata": {}
            }
            await insert_run(test_db, run_dict)

        runs = await get_runs(test_db)
        assert runs[0]["run_id"] == "run_order_2"
        assert runs[1]["run_id"] == "run_order_1"
        assert runs[2]["run_id"] == "run_order_0"

    async def test_get_runs_with_offset(self, test_db: AsyncSession):
        """Should respect offset parameter for pagination."""
        for i in range(5):
            run_dict = {
                "run_id": f"run_offset_{i}",
                "name": f"Run {i}",
                "started_at": f"2026-05-30T10:00:{i:02d}.000Z",
                "status": "success",
                "metadata": {}
            }
            await insert_run(test_db, run_dict)

        runs = await get_runs(test_db, limit=2, offset=2)
        assert len(runs) == 2
        assert runs[0]["run_id"] == "run_offset_2"


@pytest.mark.asyncio
class TestUpdateRunStatus:
    """Test run status updates."""

    async def test_update_run_status_to_success(self, test_db: AsyncSession):
        """Should update run status and ended_at."""
        run_dict = {
            "run_id": "run_status_001",
            "name": "Status Test",
            "started_at": "2026-05-30T10:00:00.000Z",
            "status": "running",
            "metadata": {}
        }
        await insert_run(test_db, run_dict)

        updated = await update_run_status(
            test_db,
            "run_status_001",
            "success",
            "2026-05-30T10:00:10.000Z",
            None
        )

        assert updated is not None
        assert updated["status"] == "success"
        assert updated["duration_ms"] == 10000

    async def test_update_run_status_to_error(self, test_db: AsyncSession):
        """Should update run status with error message."""
        run_dict = {
            "run_id": "run_error_001",
            "name": "Error Test",
            "started_at": "2026-05-30T10:00:00.000Z",
            "status": "running",
            "metadata": {}
        }
        await insert_run(test_db, run_dict)

        updated = await update_run_status(
            test_db,
            "run_error_001",
            "error",
            "2026-05-30T10:00:05.000Z",
            "Connection timeout"
        )

        assert updated["status"] == "error"
        assert updated["error_message"] == "Connection timeout"

    async def test_update_nonexistent_run(self, test_db: AsyncSession):
        """Should return None when run doesn't exist."""
        updated = await update_run_status(
            test_db,
            "nonexistent_run",
            "success",
            "2026-05-30T10:00:10.000Z",
            None
        )

        assert updated is None


@pytest.mark.asyncio
class TestGetRunDetails:
    """Test detailed run retrieval with spans."""

    async def test_get_run_details_with_spans(self, test_db: AsyncSession):
        """Should return run with all associated spans."""
        run_dict = {
            "run_id": "run_details_001",
            "name": "Details Test",
            "started_at": "2026-05-30T10:00:00.000Z",
            "status": "success",
            "metadata": {}
        }
        await insert_run(test_db, run_dict)

        span_dicts = [
            {
                "span_id": "span_detail_001",
                "run_id": "run_details_001",
                "span_type": "llm",
                "name": "llm",
                "started_at": "2026-05-30T10:00:01.000Z",
                "status": "success",
                "metadata": {}
            }
        ]
        await insert_spans_batch(test_db, span_dicts)

        details = await get_run_details(test_db, "run_details_001")

        assert details is not None
        assert details["run_id"] == "run_details_001"
        assert "spans" in details
        assert len(details["spans"]) == 1

    async def test_get_nonexistent_run_details(self, test_db: AsyncSession):
        """Should return None for non-existent run."""
        details = await get_run_details(test_db, "nonexistent")
        assert details is None


@pytest.mark.asyncio
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    async def test_empty_tags_list(self, test_db: AsyncSession):
        """Should handle empty tags gracefully."""
        run_dict = {
            "run_id": "run_empty_tags",
            "name": "Empty Tags",
            "started_at": "2026-05-30T10:00:00.000Z",
            "tags": [],
            "status": "running",
            "metadata": {}
        }
        await insert_run(test_db, run_dict)

        runs = await get_runs(test_db)
        assert len(runs) == 1

    async def test_null_optional_fields(self, test_db: AsyncSession):
        """Should handle null optional fields."""
        run_dict = {
            "run_id": "run_null_fields",
            "name": "Null Fields",
            "started_at": "2026-05-30T10:00:00.000Z",
            "session_id": None,
            "ended_at": None,
            "error_message": None,
            "status": "running",
            "metadata": {}
        }
        await insert_run(test_db, run_dict)

        runs = await get_runs(test_db)
        assert runs[0]["session_id"] is None
        assert runs[0]["ended_at"] is None

    async def test_span_with_zero_tokens(self, test_db: AsyncSession):
        """Should handle spans with zero token usage."""
        run_dict = {
            "run_id": "run_zero_tokens",
            "name": "Zero Tokens",
            "started_at": "2026-05-30T10:00:00.000Z",
            "status": "running",
            "metadata": {}
        }
        await insert_run(test_db, run_dict)

        span_dicts = [{
            "span_id": "span_zero",
            "run_id": "run_zero_tokens",
            "span_type": "tool",
            "name": "tool",
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "started_at": "2026-05-30T10:00:01.000Z",
            "status": "success",
            "metadata": {}
        }]

        await insert_spans_batch(test_db, span_dicts)

        details = await get_run_details(test_db, "run_zero_tokens")
        assert details["spans"][0]["total_tokens"] == 0
        assert float(details["spans"][0]["cost_usd"]) == 0.0

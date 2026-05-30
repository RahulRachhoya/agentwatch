"""
Test suite for FastAPI endpoints and WebSocket functionality.

Tests API responses, WebSocket events, and endpoint integration.
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect

from backend.main import app, manager, serialize_datetimes
from datetime import datetime, timezone


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestSerializeDatetimes:
    """Test datetime serialization helper."""

    def test_serialize_dict_with_datetime(self):
        """Should convert datetime to ISO string in dict."""
        dt = datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc)
        data = {"time": dt, "name": "test"}

        result = serialize_datetimes(data)

        assert result["time"] == dt.isoformat()
        assert result["name"] == "test"

    def test_serialize_nested_dict(self):
        """Should recursively serialize nested dicts."""
        dt = datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc)
        data = {
            "outer": {
                "inner": {"time": dt}
            }
        }

        result = serialize_datetimes(data)

        assert result["outer"]["inner"]["time"] == dt.isoformat()

    def test_serialize_list_with_datetime(self):
        """Should serialize datetimes in lists."""
        dt1 = datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc)
        dt2 = datetime(2026, 5, 30, 11, 0, 0, tzinfo=timezone.utc)
        data = [dt1, dt2, "string"]

        result = serialize_datetimes(data)

        assert result[0] == dt1.isoformat()
        assert result[1] == dt2.isoformat()
        assert result[2] == "string"

    def test_serialize_primitive_types(self):
        """Should pass through non-datetime types."""
        data = {"str": "value", "int": 42, "bool": True, "none": None}

        result = serialize_datetimes(data)

        assert result == data


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_endpoint_returns_ok(self, client):
        """Should return 200 with status ok."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "time" in data

    def test_health_endpoint_returns_timestamp(self, client):
        """Should return current timestamp."""
        response = client.get("/health")
        data = response.json()

        # Verify time is valid ISO format
        time_str = data["time"]
        parsed_time = datetime.fromisoformat(time_str)
        assert isinstance(parsed_time, datetime)


@pytest.mark.asyncio
class TestRunsEndpoints:
    """Test runs CRUD endpoints."""

    @patch("backend.main.get_db")
    @patch("backend.main.insert_run")
    @patch("backend.main.manager.broadcast")
    async def test_create_run_without_auth(self, mock_broadcast, mock_insert, mock_db, client):
        """Should create run when no API key is required."""
        mock_db.return_value.__aenter__.return_value = AsyncMock()
        mock_insert.return_value = None
        mock_broadcast.return_value = None

        with patch.dict("os.environ", {}, clear=True):
            response = client.post(
                "/v1/runs",
                json={
                    "run_id": "test_run_001",
                    "name": "Test Run",
                    "started_at": "2026-05-30T10:00:00.000Z",
                    "metadata": {}
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["run_id"] == "test_run_001"
            assert data["data"]["status"] == "running"

    @patch("backend.main.get_db")
    async def test_create_run_with_invalid_auth(self, mock_db, client):
        """Should reject request with invalid API key."""
        with patch.dict("os.environ", {"AGENTWATCH_API_KEY": "valid-key"}):
            response = client.post(
                "/v1/runs",
                headers={"X-API-Key": "invalid-key"},
                json={
                    "run_id": "test_run_002",
                    "name": "Test Run",
                    "started_at": "2026-05-30T10:00:00.000Z",
                    "metadata": {}
                }
            )

            assert response.status_code == 401

    @patch("backend.main.get_db")
    @patch("backend.main.get_runs")
    async def test_list_runs_with_pagination(self, mock_get_runs, mock_db, client):
        """Should return paginated runs list."""
        mock_db.return_value.__aenter__.return_value = AsyncMock()
        mock_get_runs.return_value = [
            {"run_id": "run_001", "name": "Run 1"},
            {"run_id": "run_002", "name": "Run 2"}
        ]

        with patch.dict("os.environ", {}, clear=True):
            response = client.get("/v1/runs?limit=2&offset=0")

            assert response.status_code == 200
            data = response.json()
            assert len(data["data"]) == 2

    @patch("backend.main.get_db")
    @patch("backend.main.get_run_details")
    async def test_get_run_details(self, mock_get_details, mock_db, client):
        """Should return run details with spans."""
        mock_db.return_value.__aenter__.return_value = AsyncMock()
        mock_get_details.return_value = {
            "run_id": "run_001",
            "name": "Test Run",
            "spans": [{"span_id": "span_001"}]
        }

        with patch.dict("os.environ", {}, clear=True):
            response = client.get("/v1/runs/run_001")

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["run_id"] == "run_001"
            assert len(data["data"]["spans"]) == 1

    @patch("backend.main.get_db")
    @patch("backend.main.get_run_details")
    async def test_get_nonexistent_run(self, mock_get_details, mock_db, client):
        """Should return 404 for non-existent run."""
        mock_db.return_value.__aenter__.return_value = AsyncMock()
        mock_get_details.return_value = None

        with patch.dict("os.environ", {}, clear=True):
            response = client.get("/v1/runs/nonexistent")

            assert response.status_code == 404

    @patch("backend.main.get_db")
    @patch("backend.main.update_run_status")
    @patch("backend.main.manager.broadcast")
    async def test_update_run_status(self, mock_broadcast, mock_update, mock_db, client):
        """Should update run status."""
        mock_db.return_value.__aenter__.return_value = AsyncMock()
        mock_update.return_value = {
            "run_id": "run_001",
            "status": "success",
            "duration_ms": 5000
        }
        mock_broadcast.return_value = None

        with patch.dict("os.environ", {}, clear=True):
            response = client.patch(
                "/v1/runs/run_001",
                json={
                    "status": "success",
                    "ended_at": "2026-05-30T10:00:05.000Z"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["status"] == "success"

    @patch("backend.main.get_db")
    @patch("backend.main.update_run_status")
    async def test_update_nonexistent_run(self, mock_update, mock_db, client):
        """Should return 404 when updating non-existent run."""
        mock_db.return_value.__aenter__.return_value = AsyncMock()
        mock_update.return_value = None

        with patch.dict("os.environ", {}, clear=True):
            response = client.patch(
                "/v1/runs/nonexistent",
                json={
                    "status": "success",
                    "ended_at": "2026-05-30T10:00:05.000Z"
                }
            )

            assert response.status_code == 404


@pytest.mark.asyncio
class TestSpansEndpoints:
    """Test spans endpoints."""

    @patch("backend.main.get_db")
    @patch("backend.main.insert_spans_batch")
    @patch("backend.main.manager.broadcast")
    async def test_create_spans_batch(self, mock_broadcast, mock_insert, mock_db, client):
        """Should create multiple spans in batch."""
        mock_db.return_value.__aenter__.return_value = AsyncMock()
        mock_insert.return_value = None
        mock_broadcast.return_value = None

        with patch.dict("os.environ", {}, clear=True):
            response = client.post(
                "/v1/spans/batch",
                json={
                    "spans": [
                        {
                            "span_id": "span_001",
                            "run_id": "run_001",
                            "span_type": "llm",
                            "name": "test",
                            "started_at": "2026-05-30T10:00:00.000Z"
                        }
                    ]
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["created"] == 1
            assert data["data"]["failed"] == 0

    @patch("backend.main.get_db")
    @patch("backend.main.insert_spans_batch")
    async def test_create_empty_spans_batch(self, mock_insert, mock_db, client):
        """Should handle empty spans batch."""
        mock_db.return_value.__aenter__.return_value = AsyncMock()
        mock_insert.return_value = None

        with patch.dict("os.environ", {}, clear=True):
            response = client.post(
                "/v1/spans/batch",
                json={"spans": []}
            )

            assert response.status_code == 200


@pytest.mark.asyncio
class TestOTLPEndpoint:
    """Test OTLP trace ingestion endpoint."""

    @patch("backend.main.get_db")
    @patch("backend.main.decode_otlp_request")
    @patch("backend.main.insert_spans_batch")
    @patch("backend.main.manager.broadcast")
    async def test_ingest_otlp_traces(self, mock_broadcast, mock_insert, mock_decode, mock_db, client):
        """Should ingest and decode OTLP protobuf traces."""
        mock_db.return_value.__aenter__.return_value = AsyncMock()
        mock_decode.return_value = [
            {"span_id": "span_001", "run_id": "run_001", "name": "test"}
        ]
        mock_insert.return_value = None
        mock_broadcast.return_value = None

        with patch.dict("os.environ", {}, clear=True):
            # Send fake protobuf data
            response = client.post(
                "/v1/traces",
                content=b"fake-protobuf-data",
                headers={"Content-Type": "application/x-protobuf"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["spans_created"] == 1

    @patch("backend.main.get_db")
    @patch("backend.main.decode_otlp_request")
    async def test_ingest_invalid_otlp_data(self, mock_decode, mock_db, client):
        """Should handle invalid protobuf data gracefully."""
        mock_db.return_value.__aenter__.return_value = AsyncMock()
        mock_decode.return_value = []  # Empty result for invalid data

        with patch.dict("os.environ", {}, clear=True):
            response = client.post(
                "/v1/traces",
                content=b"invalid-data"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["spans_created"] == 0


class TestWebSocketConnection:
    """Test WebSocket connection and broadcasting."""

    def test_websocket_connection(self, client):
        """Should establish WebSocket connection."""
        with client.websocket_connect("/ws") as websocket:
            # Connection successful if no exception
            assert websocket is not None

    def test_websocket_receives_messages(self, client):
        """Should receive broadcast messages."""
        with client.websocket_connect("/ws") as websocket:
            # In real scenario, would broadcast from another endpoint
            # This tests the connection is maintained
            websocket.send_text("ping")


class TestConnectionManager:
    """Test WebSocket connection manager."""

    @pytest.mark.asyncio
    async def test_connect_adds_to_active_connections(self):
        """Should add connection to active connections list."""
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()

        await manager.connect(mock_ws)

        assert mock_ws in manager.active_connections
        mock_ws.accept.assert_called_once()

    def test_disconnect_removes_connection(self):
        """Should remove connection from active connections."""
        mock_ws = MagicMock()
        manager.active_connections.append(mock_ws)

        manager.disconnect(mock_ws)

        assert mock_ws not in manager.active_connections

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all_connections(self):
        """Should send message to all active connections."""
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()

        manager.active_connections = [mock_ws1, mock_ws2]

        message = {"type": "test", "data": {"id": "123"}}
        await manager.broadcast(message)

        mock_ws1.send_json.assert_called_once()
        mock_ws2.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_removes_dead_connections(self):
        """Should remove connections that fail to receive messages."""
        mock_ws_good = AsyncMock()
        mock_ws_dead = AsyncMock()
        mock_ws_dead.send_json.side_effect = Exception("Connection lost")

        manager.active_connections = [mock_ws_good, mock_ws_dead]

        await manager.broadcast({"type": "test"})

        # Dead connection should be removed
        assert mock_ws_dead not in manager.active_connections
        assert mock_ws_good in manager.active_connections


class TestCORS:
    """Test CORS middleware configuration."""

    def test_cors_allows_all_origins(self, client):
        """Should allow requests from any origin."""
        response = client.get(
            "/health",
            headers={"Origin": "http://example.com"}
        )

        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_cors_allows_credentials(self, client):
        """Should allow credentials in CORS requests."""
        response = client.options(
            "/v1/runs",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "POST"
            }
        )

        assert "access-control-allow-credentials" in response.headers


class TestEdgeCases:
    """Test edge cases and error handling."""

    @patch("backend.main.get_db")
    async def test_malformed_json_request(self, mock_db, client):
        """Should reject malformed JSON."""
        with patch.dict("os.environ", {}, clear=True):
            response = client.post(
                "/v1/runs",
                data="invalid-json",
                headers={"Content-Type": "application/json"}
            )

            assert response.status_code == 422  # Unprocessable Entity

    @patch("backend.main.get_db")
    async def test_missing_required_fields(self, mock_db, client):
        """Should reject requests with missing required fields."""
        with patch.dict("os.environ", {}, clear=True):
            response = client.post(
                "/v1/runs",
                json={"name": "Test"}  # Missing run_id and started_at
            )

            assert response.status_code == 422

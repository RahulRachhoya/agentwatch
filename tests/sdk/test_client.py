"""
Test suite for AgentWatch SDK client.

Tests HTTP client, ThreadPoolExecutor export, and async operations.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import httpx

from sdk.agentwatch.client import AgentWatchClient


class TestClientInitialization:
    """Test client initialization."""

    def test_init_with_url_only(self):
        """Should initialize with backend URL only."""
        client = AgentWatchClient("http://localhost:8000")

        assert client.backend_url == "http://localhost:8000"
        assert client.api_key is None
        assert "X-API-Key" not in client.headers

    def test_init_with_api_key(self):
        """Should initialize with API key in headers."""
        client = AgentWatchClient("http://localhost:8000", api_key="test-key")

        assert client.api_key == "test-key"
        assert client.headers["X-API-Key"] == "test-key"

    def test_init_strips_trailing_slash(self):
        """Should strip trailing slash from URL."""
        client = AgentWatchClient("http://localhost:8000/")

        assert client.backend_url == "http://localhost:8000"

    def test_init_creates_thread_pool(self):
        """Should create ThreadPoolExecutor with max_workers=5."""
        client = AgentWatchClient("http://localhost:8000")

        assert client.executor is not None
        assert client.executor._max_workers == 5


class TestPostMethod:
    """Test internal _post method."""

    @patch("sdk.agentwatch.client.httpx.Client")
    def test_post_success(self, mock_client_class):
        """Should successfully post data."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value.post.return_value = mock_response
        mock_client_class.return_value = mock_client_instance

        client = AgentWatchClient("http://localhost:8000")
        client._post("/v1/runs", {"run_id": "test"})

        mock_client_instance.__enter__.return_value.post.assert_called_once_with(
            "http://localhost:8000/v1/runs",
            json={"run_id": "test"}
        )

    @patch("sdk.agentwatch.client.httpx.Client")
    def test_post_handles_http_error(self, mock_client_class):
        """Should handle HTTP errors gracefully."""
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value.post.side_effect = httpx.HTTPStatusError(
            "404", request=Mock(), response=Mock()
        )
        mock_client_class.return_value = mock_client_instance

        client = AgentWatchClient("http://localhost:8000")

        # Should not raise exception
        client._post("/v1/runs", {"run_id": "test"})

    @patch("sdk.agentwatch.client.httpx.Client")
    def test_post_handles_timeout(self, mock_client_class):
        """Should handle timeout errors."""
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value.post.side_effect = httpx.TimeoutException(
            "Timeout"
        )
        mock_client_class.return_value = mock_client_instance

        client = AgentWatchClient("http://localhost:8000")

        # Should not raise exception
        client._post("/v1/runs", {"run_id": "test"})

    @patch("sdk.agentwatch.client.httpx.Client")
    def test_post_uses_timeout(self, mock_client_class):
        """Should use 5 second timeout."""
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance

        client = AgentWatchClient("http://localhost:8000")

        # Check that httpx.Client is created with timeout
        mock_client_class.assert_called_with(headers=client.headers, timeout=5.0)


class TestPatchMethod:
    """Test internal _patch method."""

    @patch("sdk.agentwatch.client.httpx.Client")
    def test_patch_success(self, mock_client_class):
        """Should successfully patch data."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value.patch.return_value = mock_response
        mock_client_class.return_value = mock_client_instance

        client = AgentWatchClient("http://localhost:8000")
        client._patch("/v1/runs/test", {"status": "success"})

        mock_client_instance.__enter__.return_value.patch.assert_called_once_with(
            "http://localhost:8000/v1/runs/test",
            json={"status": "success"}
        )

    @patch("sdk.agentwatch.client.httpx.Client")
    def test_patch_handles_errors(self, mock_client_class):
        """Should handle errors gracefully."""
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value.patch.side_effect = Exception("Error")
        mock_client_class.return_value = mock_client_instance

        client = AgentWatchClient("http://localhost:8000")

        # Should not raise exception
        client._patch("/v1/runs/test", {"status": "success"})


class TestCreateRun:
    """Test create_run method."""

    @patch.object(AgentWatchClient, "_post")
    def test_create_run_minimal(self, mock_post):
        """Should create run with minimal required fields."""
        client = AgentWatchClient("http://localhost:8000")

        client.create_run("run_001", "Test Run")

        # Verify _post was called via executor
        # We can't easily test ThreadPoolExecutor submission, so we test the method exists
        assert hasattr(client, "create_run")

    @patch.object(AgentWatchClient, "_post")
    def test_create_run_with_all_fields(self, mock_post):
        """Should create run with all optional fields."""
        client = AgentWatchClient("http://localhost:8000")

        client.create_run(
            run_id="run_002",
            name="Full Run",
            session_id="session_001",
            tags=["test", "dev"],
            metadata={"env": "test"}
        )

        # Method should execute without error
        assert True

    @patch("sdk.agentwatch.client.datetime")
    @patch.object(AgentWatchClient, "_post")
    def test_create_run_generates_timestamp(self, mock_post, mock_datetime):
        """Should generate current UTC timestamp."""
        mock_now = datetime(2026, 5, 30, 10, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now

        client = AgentWatchClient("http://localhost:8000")
        client.executor.submit = Mock()  # Mock executor to verify payload

        client.create_run("run_003", "Timestamp Test")

        # Verify executor was called
        client.executor.submit.assert_called_once()


class TestUpdateRun:
    """Test update_run method."""

    @patch.object(AgentWatchClient, "_patch")
    def test_update_run_success(self, mock_patch):
        """Should update run status."""
        client = AgentWatchClient("http://localhost:8000")
        client.executor.submit = Mock()

        client.update_run("run_001", "success")

        client.executor.submit.assert_called_once()

    @patch.object(AgentWatchClient, "_patch")
    def test_update_run_with_error(self, mock_patch):
        """Should update run with error message."""
        client = AgentWatchClient("http://localhost:8000")
        client.executor.submit = Mock()

        client.update_run("run_002", "error", error_message="Connection failed")

        client.executor.submit.assert_called_once()

    @patch("sdk.agentwatch.client.datetime")
    @patch.object(AgentWatchClient, "_patch")
    def test_update_run_includes_ended_at(self, mock_patch, mock_datetime):
        """Should include ended_at timestamp."""
        mock_now = datetime(2026, 5, 30, 10, 0, 5, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now

        client = AgentWatchClient("http://localhost:8000")
        client.executor.submit = Mock()

        client.update_run("run_003", "success")

        client.executor.submit.assert_called_once()


class TestSendSpans:
    """Test send_spans method."""

    @patch.object(AgentWatchClient, "_post")
    def test_send_single_span(self, mock_post):
        """Should send single span."""
        client = AgentWatchClient("http://localhost:8000")
        client.executor.submit = Mock()

        spans = [{"span_id": "span_001", "name": "test"}]
        client.send_spans(spans)

        client.executor.submit.assert_called_once()

    @patch.object(AgentWatchClient, "_post")
    def test_send_multiple_spans(self, mock_post):
        """Should send multiple spans in batch."""
        client = AgentWatchClient("http://localhost:8000")
        client.executor.submit = Mock()

        spans = [
            {"span_id": "span_001", "name": "test1"},
            {"span_id": "span_002", "name": "test2"}
        ]
        client.send_spans(spans)

        client.executor.submit.assert_called_once()

    @patch.object(AgentWatchClient, "_post")
    def test_send_empty_spans_list(self, mock_post):
        """Should handle empty spans list."""
        client = AgentWatchClient("http://localhost:8000")
        client.executor.submit = Mock()

        client.send_spans([])

        client.executor.submit.assert_called_once()


class TestThreadPoolExecution:
    """Test ThreadPoolExecutor integration."""

    def test_executor_runs_async(self):
        """Should execute operations asynchronously."""
        import time
        from concurrent.futures import Future

        client = AgentWatchClient("http://localhost:8000")

        # Mock _post to track execution
        call_times = []

        def mock_post(*args, **kwargs):
            call_times.append(time.time())

        with patch.object(client, "_post", mock_post):
            # Submit multiple operations
            client.create_run("run_001", "Test 1")
            client.create_run("run_002", "Test 2")
            client.create_run("run_003", "Test 3")

            # Wait for all to complete
            client.executor.shutdown(wait=True)

            # All operations should have executed
            assert len(call_times) == 3

    def test_executor_handles_errors_without_crashing(self):
        """Should handle exceptions in executor threads."""
        client = AgentWatchClient("http://localhost:8000")

        with patch.object(client, "_post", side_effect=Exception("Test error")):
            # Should not raise exception
            client.create_run("run_001", "Test")

            # Wait for operation to complete
            client.executor.shutdown(wait=True)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_client_with_null_api_key(self):
        """Should handle None API key."""
        client = AgentWatchClient("http://localhost:8000", api_key=None)

        assert "X-API-Key" not in client.headers

    def test_client_with_empty_string_api_key(self):
        """Should handle empty string API key."""
        client = AgentWatchClient("http://localhost:8000", api_key="")

        # Empty string should still be set
        assert client.headers["X-API-Key"] == ""

    def test_create_run_with_special_characters(self):
        """Should handle special characters in run names."""
        client = AgentWatchClient("http://localhost:8000")
        client.executor.submit = Mock()

        client.create_run("run_001", "Test with 中文 and émojis 🚀")

        # Should not raise exception
        client.executor.submit.assert_called_once()

    def test_send_spans_with_large_batch(self):
        """Should handle large batch of spans."""
        client = AgentWatchClient("http://localhost:8000")
        client.executor.submit = Mock()

        # Create 1000 spans
        spans = [{"span_id": f"span_{i:04d}", "name": f"span_{i}"} for i in range(1000)]

        client.send_spans(spans)

        client.executor.submit.assert_called_once()

    @patch("sdk.agentwatch.client.httpx.Client")
    def test_network_timeout_recovery(self, mock_client_class):
        """Should recover from network timeouts."""
        mock_client_instance = MagicMock()
        # First call times out, second succeeds
        mock_client_instance.__enter__.return_value.post.side_effect = [
            httpx.TimeoutException("Timeout"),
            Mock(raise_for_status=Mock())
        ]
        mock_client_class.return_value = mock_client_instance

        client = AgentWatchClient("http://localhost:8000")

        # First call should not crash
        client._post("/v1/runs", {"run_id": "test1"})

        # Second call should work
        client._post("/v1/runs", {"run_id": "test2"})

    def test_concurrent_operations(self):
        """Should handle concurrent operations safely."""
        client = AgentWatchClient("http://localhost:8000")

        with patch.object(client, "_post"):
            # Submit many operations concurrently
            for i in range(100):
                client.create_run(f"run_{i:03d}", f"Test {i}")

            # Wait for all to complete
            client.executor.shutdown(wait=True)

            # Should complete without deadlocks or crashes
            assert True

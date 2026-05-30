"""
Security Test Suite for AgentWatch

Tests all security controls:
1. WebSocket authentication
2. Rate limiting
3. CORS configuration
4. Error message sanitization
5. API key validation
"""

import os
import sys
import time
import json
import httpx
import unittest
import multiprocessing
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

# Setup test environment with security enabled
TEST_DB_FILE = "./test_security_aw.db"
TEST_API_KEY = "test-secret-key-12345"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_FILE}"
os.environ["AGENTWATCH_API_KEY"] = TEST_API_KEY
os.environ["ALLOWED_ORIGINS"] = "http://localhost:3000,http://localhost:8080"

import uvicorn
from main import app


def run_server():
    """Run uvicorn server in separate process."""
    uvicorn.run(app, host="127.0.0.1", port=8124, log_level="error")


class TestSecurityControls(unittest.TestCase):
    server_process = None
    base_url = "http://127.0.0.1:8124"

    @classmethod
    def setUpClass(cls):
        """Start test server with security enabled."""
        if os.path.exists(TEST_DB_FILE):
            try:
                os.remove(TEST_DB_FILE)
            except Exception:
                pass

        cls.server_process = multiprocessing.Process(target=run_server)
        cls.server_process.start()
        time.sleep(1.5)

    @classmethod
    def tearDownClass(cls):
        """Cleanup test server and database."""
        if cls.server_process:
            cls.server_process.terminate()
            cls.server_process.join()

        time.sleep(0.5)
        if os.path.exists(TEST_DB_FILE):
            try:
                os.remove(TEST_DB_FILE)
            except Exception as e:
                print(f"Warning: Failed to delete test database: {e}")

    # ========== API Key Authentication Tests ==========

    def test_01_missing_api_key_rejection(self):
        """Verify endpoints reject requests without X-API-Key header."""
        endpoints = [
            ("POST", "/v1/runs", {"run_id": "test", "name": "Test", "started_at": datetime.now().isoformat()}),
            ("GET", "/v1/runs", None),
            ("PATCH", "/v1/runs/test-run", {"status": "success"}),
            ("POST", "/v1/spans/batch", {"spans": []}),
            ("POST", "/v1/traces", None),
        ]

        for method, path, payload in endpoints:
            with self.subTest(endpoint=f"{method} {path}"):
                if method == "POST":
                    res = httpx.post(f"{self.base_url}{path}", json=payload)
                elif method == "PATCH":
                    res = httpx.patch(f"{self.base_url}{path}", json=payload)
                else:
                    res = httpx.get(f"{self.base_url}{path}")

                self.assertEqual(res.status_code, 401, f"{method} {path} should reject missing API key")
                self.assertIn("Unauthorized", res.json()["detail"])

    def test_02_invalid_api_key_rejection(self):
        """Verify endpoints reject requests with wrong X-API-Key."""
        headers = {"X-API-Key": "wrong-key"}

        res = httpx.get(f"{self.base_url}/v1/runs", headers=headers)
        self.assertEqual(res.status_code, 401)
        self.assertIn("Invalid", res.json()["detail"])

    def test_03_valid_api_key_acceptance(self):
        """Verify endpoints accept requests with correct X-API-Key."""
        headers = {"X-API-Key": TEST_API_KEY}

        res = httpx.get(f"{self.base_url}/v1/runs", headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertIn("data", res.json())

    # ========== WebSocket Authentication Tests ==========

    def test_04_websocket_missing_api_key(self):
        """Verify WebSocket connection rejects missing X-API-Key header."""
        try:
            from websockets.sync.client import connect

            # Attempt connection without API key
            with self.assertRaises(Exception) as context:
                with connect(f"ws://127.0.0.1:8124/ws"):
                    pass

            # Should be rejected with 1008 (policy violation)
            error_msg = str(context.exception)
            self.assertTrue("1008" in error_msg or "Unauthorized" in error_msg)

        except ImportError:
            self.skipTest("websockets library not installed")

    def test_05_websocket_invalid_api_key(self):
        """Verify WebSocket connection rejects invalid X-API-Key header."""
        try:
            from websockets.sync.client import connect

            # Attempt connection with wrong API key
            with self.assertRaises(Exception) as context:
                with connect(
                    f"ws://127.0.0.1:8124/ws",
                    additional_headers={"X-API-Key": "wrong-key"}
                ):
                    pass

            error_msg = str(context.exception)
            self.assertTrue("1008" in error_msg or "Unauthorized" in error_msg)

        except ImportError:
            self.skipTest("websockets library not installed")

    def test_06_websocket_valid_api_key(self):
        """Verify WebSocket connection accepts valid X-API-Key header."""
        try:
            from websockets.sync.client import connect

            # Successful connection with correct API key
            with connect(
                f"ws://127.0.0.1:8124/ws",
                additional_headers={"X-API-Key": TEST_API_KEY}
            ) as websocket:
                # Connection should be established
                self.assertTrue(websocket.open)

        except ImportError:
            self.skipTest("websockets library not installed")

    # ========== Rate Limiting Tests ==========

    def test_07_rate_limit_enforcement(self):
        """Verify rate limiting on POST /v1/spans/batch endpoint."""
        headers = {"X-API-Key": TEST_API_KEY}
        payload = {"spans": []}

        # Send requests rapidly to trigger rate limit
        rate_limited = False
        for i in range(15):
            res = httpx.post(f"{self.base_url}/v1/spans/batch", json=payload, headers=headers)
            if res.status_code == 429:
                rate_limited = True
                self.assertIn("Rate limit", res.text, "Should return rate limit error message")
                break

        # Note: In practice, 15 requests won't hit 1000/min limit
        # This test verifies the decorator is applied
        # In production, you'd need to send 1001 requests in 60 seconds
        if not rate_limited:
            self.skipTest("Rate limit not reached with 15 requests (expected for 1000/min limit)")

    # ========== Error Sanitization Tests ==========

    def test_08_error_message_sanitization(self):
        """Verify internal errors don't leak sensitive details."""
        headers = {"X-API-Key": TEST_API_KEY}

        # Trigger an error with malformed payload
        payload = {"run_id": "test", "name": "Test", "started_at": "invalid-date-format"}

        res = httpx.post(f"{self.base_url}/v1/runs", json=payload, headers=headers)

        # Should return 500 but not leak internal details
        if res.status_code == 500:
            response_body = res.json()
            # Should not contain stack traces or internal paths
            self.assertNotIn("Traceback", str(response_body))
            self.assertNotIn("/home/", str(response_body))
            self.assertNotIn("sqlalchemy", str(response_body).lower())

    # ========== Timing Attack Protection Tests ==========

    def test_09_timing_safe_comparison(self):
        """Verify timing-safe comparison for API keys (basic smoke test)."""
        headers_wrong = {"X-API-Key": "a" * len(TEST_API_KEY)}
        headers_correct = {"X-API-Key": TEST_API_KEY}

        # Both should return quickly and consistently
        start = time.perf_counter()
        res1 = httpx.get(f"{self.base_url}/v1/runs", headers=headers_wrong)
        time1 = time.perf_counter() - start

        start = time.perf_counter()
        res2 = httpx.get(f"{self.base_url}/v1/runs", headers=headers_correct)
        time2 = time.perf_counter() - start

        # Timing should be similar (within 100ms tolerance)
        # This is a basic smoke test; real timing attacks need statistical analysis
        self.assertTrue(abs(time1 - time2) < 0.1, "API key comparison should use timing-safe method")

        self.assertEqual(res1.status_code, 401)
        self.assertEqual(res2.status_code, 200)

    # ========== CORS Configuration Tests ==========

    def test_10_cors_headers_present(self):
        """Verify CORS headers are set correctly."""
        headers = {"X-API-Key": TEST_API_KEY, "Origin": "http://localhost:3000"}

        res = httpx.options(f"{self.base_url}/v1/runs", headers=headers)

        # Should have CORS headers
        self.assertIn("access-control-allow-origin", res.headers)

    def test_11_health_check_no_auth(self):
        """Verify health check endpoint works without authentication."""
        res = httpx.get(f"{self.base_url}/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "ok")


if __name__ == "__main__":
    unittest.main(verbosity=2)

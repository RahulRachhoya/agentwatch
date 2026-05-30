"""
Test suite for authentication and API key verification.

Tests timing-safe comparison and authorization logic.
"""
import pytest
import os
from unittest.mock import patch
from fastapi import HTTPException

from backend.auth import verify_api_key


class TestVerifyApiKey:
    """Test API key verification logic."""

    def test_no_api_key_required_when_env_not_set(self):
        """Should allow access when AGENTWATCH_API_KEY is not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Should not raise exception
            result = verify_api_key(x_api_key=None)
            assert result is True

    def test_missing_api_key_when_required(self):
        """Should raise 401 when API key is required but not provided."""
        with patch.dict(os.environ, {"AGENTWATCH_API_KEY": "secret-key"}):
            with pytest.raises(HTTPException) as exc_info:
                verify_api_key(x_api_key=None)

            assert exc_info.value.status_code == 401
            assert "Missing API Key" in exc_info.value.detail

    def test_invalid_api_key(self):
        """Should raise 401 when API key doesn't match."""
        with patch.dict(os.environ, {"AGENTWATCH_API_KEY": "correct-key"}):
            with pytest.raises(HTTPException) as exc_info:
                verify_api_key(x_api_key="wrong-key")

            assert exc_info.value.status_code == 401
            assert "Invalid API Key" in exc_info.value.detail

    def test_valid_api_key(self):
        """Should allow access with correct API key."""
        with patch.dict(os.environ, {"AGENTWATCH_API_KEY": "correct-key"}):
            result = verify_api_key(x_api_key="correct-key")
            assert result is True

    def test_timing_safe_comparison(self):
        """Should use secrets.compare_digest for timing attack prevention."""
        # This test verifies that the function uses timing-safe comparison
        # by ensuring both valid and invalid keys take similar time
        import time

        with patch.dict(os.environ, {"AGENTWATCH_API_KEY": "a" * 64}):
            # Test with correct key
            start = time.perf_counter()
            try:
                verify_api_key(x_api_key="a" * 64)
            except HTTPException:
                pass
            time_correct = time.perf_counter() - start

            # Test with wrong key (same length)
            start = time.perf_counter()
            try:
                verify_api_key(x_api_key="b" * 64)
            except HTTPException:
                pass
            time_wrong = time.perf_counter() - start

            # Timing should be similar (within reasonable variance)
            # This is a heuristic test - the key point is we're using secrets.compare_digest
            assert abs(time_correct - time_wrong) < 0.001  # Less than 1ms difference

    def test_empty_string_api_key(self):
        """Should reject empty string as API key."""
        with patch.dict(os.environ, {"AGENTWATCH_API_KEY": "valid-key"}):
            with pytest.raises(HTTPException) as exc_info:
                verify_api_key(x_api_key="")

            assert exc_info.value.status_code == 401

    def test_whitespace_api_key(self):
        """Should reject whitespace-only API key."""
        with patch.dict(os.environ, {"AGENTWATCH_API_KEY": "valid-key"}):
            with pytest.raises(HTTPException) as exc_info:
                verify_api_key(x_api_key="   ")

            assert exc_info.value.status_code == 401

    def test_case_sensitive_comparison(self):
        """Should perform case-sensitive comparison."""
        with patch.dict(os.environ, {"AGENTWATCH_API_KEY": "SecretKey123"}):
            # Lowercase should fail
            with pytest.raises(HTTPException):
                verify_api_key(x_api_key="secretkey123")

            # Uppercase should fail
            with pytest.raises(HTTPException):
                verify_api_key(x_api_key="SECRETKEY123")

            # Exact match should succeed
            result = verify_api_key(x_api_key="SecretKey123")
            assert result is True

    def test_special_characters_in_key(self):
        """Should handle special characters in API keys."""
        special_key = "key!@#$%^&*()_+-=[]{}|;:',.<>?/~`"
        with patch.dict(os.environ, {"AGENTWATCH_API_KEY": special_key}):
            result = verify_api_key(x_api_key=special_key)
            assert result is True

    def test_unicode_in_key(self):
        """Should handle Unicode characters in API keys."""
        unicode_key = "key-with-emoji-🔒-and-中文"
        with patch.dict(os.environ, {"AGENTWATCH_API_KEY": unicode_key}):
            result = verify_api_key(x_api_key=unicode_key)
            assert result is True


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_long_api_key(self):
        """Should handle very long API keys."""
        long_key = "a" * 10000
        with patch.dict(os.environ, {"AGENTWATCH_API_KEY": long_key}):
            result = verify_api_key(x_api_key=long_key)
            assert result is True

    def test_api_key_with_newlines(self):
        """Should not match keys with embedded newlines."""
        with patch.dict(os.environ, {"AGENTWATCH_API_KEY": "valid-key"}):
            with pytest.raises(HTTPException):
                verify_api_key(x_api_key="valid-key\n")

            with pytest.raises(HTTPException):
                verify_api_key(x_api_key="\nvalid-key")

    def test_null_byte_in_key(self):
        """Should handle null bytes in keys."""
        with patch.dict(os.environ, {"AGENTWATCH_API_KEY": "valid-key"}):
            with pytest.raises(HTTPException):
                verify_api_key(x_api_key="valid\x00key")


class TestSecurityProperties:
    """Test security properties of the authentication system."""

    def test_constant_time_comparison_property(self):
        """Verify that secrets.compare_digest is used (constant-time)."""
        # This test ensures we're using the secure comparison method
        # by importing and checking the function's implementation
        from backend import auth
        import inspect

        source = inspect.getsource(auth.verify_api_key)
        assert "secrets.compare_digest" in source, \
            "Must use secrets.compare_digest for timing-safe comparison"

    def test_no_info_leakage_in_error_messages(self):
        """Should not leak information about key format in errors."""
        with patch.dict(os.environ, {"AGENTWATCH_API_KEY": "secret"}):
            try:
                verify_api_key(x_api_key="wrong")
            except HTTPException as e:
                # Error message should not reveal key format, length, or partial matches
                assert "secret" not in e.detail.lower()
                assert "length" not in e.detail.lower()
                assert "format" not in e.detail.lower()

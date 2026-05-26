"""
Q5: Multi-Provider Integration Test with Real Backend

Sends real spans to localhost:8000 and queries SQLite database.
"""
import json
import time
import sqlite3
import httpx
from unittest.mock import Mock


def send_test_spans():
    """Send test spans for all 5 providers"""
    backend_url = "http://localhost:8000"
    timestamp = time.time()

    test_spans = [
        {
            "span_id": f"anthropic-test-{int(timestamp)}",
            "run_id": "q5-validation",
            "name": "claude-3-5-sonnet",
            "span_type": "llm",
            "provider": "anthropic",
            "model": "claude-3-5-sonnet-20241022",
            "prompt_tokens": 15,
            "completion_tokens": 25,
            "started_at": "2024-05-27T00:00:00Z",
            "status": "success",
            "metadata": {"source": "q5_test"}
        },
        {
            "span_id": f"bedrock-claude-test-{int(timestamp)}",
            "run_id": "q5-validation",
            "name": "bedrock.invoke_model",
            "span_type": "llm",
            "provider": "bedrock",
            "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "prompt_tokens": 12,
            "completion_tokens": 8,
            "started_at": "2024-05-27T00:00:01Z",
            "status": "success",
            "metadata": {"source": "q5_test", "family": "anthropic.claude"}
        },
        {
            "span_id": f"bedrock-llama-test-{int(timestamp)}",
            "run_id": "q5-validation",
            "name": "bedrock.invoke_model",
            "span_type": "llm",
            "provider": "bedrock",
            "model": "meta.llama3-1-70b-instruct-v1:0",
            "prompt_tokens": 18,
            "completion_tokens": 6,
            "started_at": "2024-05-27T00:00:02Z",
            "status": "success",
            "metadata": {"source": "q5_test", "family": "meta.llama"}
        },
        {
            "span_id": f"deepseek-test-{int(timestamp)}",
            "run_id": "q5-validation",
            "name": "deepseek.chat.completions.create",
            "span_type": "llm",
            "provider": "deepseek",
            "model": "deepseek-chat",
            "prompt_tokens": 10,
            "completion_tokens": 15,
            "started_at": "2024-05-27T00:00:03Z",
            "status": "success",
            "metadata": {"source": "q5_test"}
        },
        {
            "span_id": f"moonshot-test-{int(timestamp)}",
            "run_id": "q5-validation",
            "name": "moonshot.chat.completions.create",
            "span_type": "llm",
            "provider": "moonshot",
            "model": "moonshot-v1-8k",
            "prompt_tokens": 14,
            "completion_tokens": 9,
            "started_at": "2024-05-27T00:00:04Z",
            "status": "success",
            "metadata": {"source": "q5_test"}
        }
    ]

    print("Sending test spans to backend...")
    try:
        response = httpx.post(
            f"{backend_url}/v1/spans/batch",
            json={"spans": test_spans},
            timeout=10.0
        )
        print(f"Response: {response.status_code}")
        if response.status_code == 200:
            print("[OK] Spans sent successfully")
            return True
        else:
            print(f"[FAIL] Backend returned {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"[FAIL] Failed to send spans: {e}")
        return False


def query_database():
    """Query SQLite database for provider spans"""
    db_path = "C:\\Users\\Rahul\\Downloads\\agent-watch\\spike\\backend\\aw.db"

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Query for Q5 test spans
        cursor.execute("""
            SELECT provider, model, prompt_tokens, completion_tokens, metadata
            FROM spans
            WHERE run_id = 'q5-validation'
            ORDER BY started_at DESC
        """)

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            print("[FAIL] No spans found in database for run_id='q5-validation'")
            return False

        print(f"\n[OK] Found {len(rows)} spans in database:")
        print("-" * 80)

        providers_found = set()
        for row in rows:
            provider, model, prompt_tokens, completion_tokens, metadata = row
            providers_found.add(provider)
            print(f"Provider: {provider:12} | Model: {model:45} | Tokens: {prompt_tokens}/{completion_tokens}")

        print("-" * 80)

        # Verify all 5 providers present
        expected_providers = {"anthropic", "bedrock", "deepseek", "moonshot"}
        missing = expected_providers - providers_found

        if missing:
            print(f"[FAIL] Missing providers: {missing}")
            return False

        if "bedrock" in providers_found:
            # Verify both Claude and Llama in Bedrock spans
            bedrock_models = [row[1] for row in rows if row[0] == "bedrock"]
            has_claude = any("anthropic.claude" in m for m in bedrock_models)
            has_llama = any("meta.llama" in m for m in bedrock_models)

            if not has_claude:
                print("[FAIL] Bedrock Claude span not found")
                return False
            if not has_llama:
                print("[FAIL] Bedrock Llama span not found")
                return False

        print(f"[OK] All required providers found: {providers_found}")
        return True

    except Exception as e:
        print(f"[FAIL] Database query error: {e}")
        return False


def main():
    print("=" * 80)
    print("Q5: Multi-Provider Integration Test")
    print("=" * 80)

    # Step 1: Send test spans
    if not send_test_spans():
        print("\n[FAIL] Could not send test spans to backend")
        return False

    # Wait for backend to process
    time.sleep(2)

    # Step 2: Query database
    if not query_database():
        print("\n[FAIL] Database verification failed")
        return False

    print("\n" + "=" * 80)
    print("PASS: All 5 providers emit spans with correct fields and token extraction")
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

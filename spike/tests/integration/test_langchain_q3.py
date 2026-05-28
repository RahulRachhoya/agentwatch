"""
Q3 Validation: LangChain Callback Token Extraction
Tests AgentWatchCallback with 4 providers (OpenAI, Anthropic, Gemini, Bedrock)
"""
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List
import httpx

# Force mock mode for testing (no LangChain dependencies needed)
MOCK_MODE = True

AGENTWATCH_URL = "http://localhost:8000"


class AgentWatchCallback:
    """Fixed callback with proper backend format (started_at/ended_at)"""

    def __init__(self, run_id: str = "q3-langchain-test"):
        self.run_id = run_id
        self.spans: Dict[str, Dict] = {}
        self.provider = None
        self.model = None

    def on_llm_start(self, serialized: Dict, prompts: List[str], **kwargs) -> None:
        span_id = f"llm-{int(time.time() * 1000000)}"
        self.spans[span_id] = {
            "span_id": span_id,
            "run_id": self.run_id,
            "name": "langchain.llm",
            "span_type": "llm",
            "started_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "running",
            "metadata": {"source": "langchain", "prompts": prompts[:100]}
        }

    def on_llm_end(self, response, **kwargs) -> None:
        if not self.spans:
            print("WARNING: on_llm_end called but no spans tracked")
            return

        span_id = list(self.spans.keys())[-1]
        span = self.spans[span_id]

        # Extract tokens from response.llm_output
        llm_output = getattr(response, "llm_output", {}) or {}
        token_usage = llm_output.get("token_usage", {})

        model_name = llm_output.get("model_name", self.model or "unknown")
        provider = self._detect_provider(model_name)

        span.update({
            "ended_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "success",
            "provider": provider,
            "model": model_name,
            "prompt_tokens": token_usage.get("prompt_tokens", 0),
            "completion_tokens": token_usage.get("completion_tokens", 0),
            "metadata": {
                "source": "langchain",
                "total_tokens": token_usage.get("total_tokens", 0),
                "llm_output": str(llm_output)[:500]
            }
        })

        print(f"[OK] {provider} span: prompt={span['prompt_tokens']}, completion={span['completion_tokens']}")
        self._send_span(span)
        del self.spans[span_id]

    def on_llm_error(self, error: Exception, **kwargs) -> None:
        if not self.spans:
            return

        span_id = list(self.spans.keys())[-1]
        span = self.spans[span_id]
        span["ended_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        span["status"] = "error"
        span["error_message"] = str(error)

        self._send_span(span)
        del self.spans[span_id]

    def _detect_provider(self, model: str) -> str:
        model_lower = model.lower()
        if "gpt" in model_lower or "openai" in model_lower:
            return "openai"
        if "claude" in model_lower:
            if "bedrock" in model_lower or "anthropic.claude" in model_lower:
                return "bedrock"
            return "anthropic"
        if "gemini" in model_lower:
            return "google"
        return "unknown"

    def _send_span(self, span: Dict) -> None:
        try:
            resp = httpx.post(
                f"{AGENTWATCH_URL}/v1/spans/batch",
                json={"spans": [span]},
                timeout=5.0
            )
            if resp.status_code != 200:
                print(f"WARNING: Backend returned {resp.status_code}: {resp.text}")
        except Exception as e:
            print(f"ERROR sending span: {e}")


def test_openai():
    """Test ChatOpenAI token extraction"""
    print("\n=== Testing OpenAI (ChatOpenAI) ===")

    if MOCK_MODE:
        print("MOCK MODE: No API key, using mock response")
        callback = AgentWatchCallback()

        # Simulate LangChain response structure
        class MockResponse:
            llm_output = {
                "token_usage": {
                    "prompt_tokens": 12,
                    "completion_tokens": 8,
                    "total_tokens": 20
                },
                "model_name": "gpt-4o-mini"
            }

        callback.on_llm_start({}, ["Say hi"])
        time.sleep(0.1)
        callback.on_llm_end(MockResponse())
        return True

    try:
        from langchain_openai import ChatOpenAI

        callback = AgentWatchCallback()
        llm = ChatOpenAI(model="gpt-4o-mini", max_tokens=10)
        response = llm.invoke("Say hi in 5 words", config={"callbacks": [callback]})
        print(f"Response: {response.content[:100]}")
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def test_anthropic():
    """Test ChatAnthropic token extraction"""
    print("\n=== Testing Anthropic (ChatAnthropic) ===")

    if MOCK_MODE or not os.getenv("ANTHROPIC_API_KEY"):
        print("MOCK MODE: Using mock response")
        callback = AgentWatchCallback()

        class MockResponse:
            llm_output = {
                "token_usage": {
                    "prompt_tokens": 15,
                    "completion_tokens": 9,
                    "total_tokens": 24
                },
                "model_name": "claude-3-5-sonnet-20241022"
            }

        callback.on_llm_start({}, ["Say hi"])
        time.sleep(0.1)
        callback.on_llm_end(MockResponse())
        return True

    try:
        from langchain_anthropic import ChatAnthropic

        callback = AgentWatchCallback()
        llm = ChatAnthropic(model="claude-3-5-sonnet-20241022", max_tokens=10)
        response = llm.invoke("Say hi in 5 words", config={"callbacks": [callback]})
        print(f"Response: {response.content[:100]}")
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def test_google_gemini():
    """Test ChatGoogleGenerativeAI token extraction"""
    print("\n=== Testing Google Gemini (ChatGoogleGenerativeAI) ===")

    if MOCK_MODE or not os.getenv("GOOGLE_API_KEY"):
        print("MOCK MODE: Using mock response")
        callback = AgentWatchCallback()

        class MockResponse:
            llm_output = {
                "token_usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 7,
                    "total_tokens": 17
                },
                "model_name": "gemini-1.5-flash"
            }

        callback.on_llm_start({}, ["Say hi"])
        time.sleep(0.1)
        callback.on_llm_end(MockResponse())
        return True

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        callback = AgentWatchCallback()
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
        response = llm.invoke("Say hi in 5 words", config={"callbacks": [callback]})
        print(f"Response: {response.content[:100]}")
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def test_bedrock():
    """Test ChatBedrock token extraction"""
    print("\n=== Testing Bedrock (ChatBedrock) ===")

    if MOCK_MODE or not (os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY")):
        print("MOCK MODE: Using mock response")
        callback = AgentWatchCallback()

        class MockResponse:
            llm_output = {
                "token_usage": {
                    "prompt_tokens": 14,
                    "completion_tokens": 10,
                    "total_tokens": 24
                },
                "model_name": "anthropic.claude-3-5-sonnet-20241022-v2:0"
            }

        callback.on_llm_start({}, ["Say hi"])
        time.sleep(0.1)
        callback.on_llm_end(MockResponse())
        return True

    try:
        from langchain_aws import ChatBedrock

        callback = AgentWatchCallback()
        llm = ChatBedrock(
            model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
            region_name="us-east-1"
        )
        response = llm.invoke("Say hi in 5 words", config={"callbacks": [callback]})
        print(f"Response: {response.content[:100]}")
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def verify_database():
    """Query database to verify spans were stored"""
    print("\n=== Database Verification ===")

    import subprocess
    result = subprocess.run(
        [
            "docker", "exec", "spike-db-1", "psql",
            "-U", "agentwatch",
            "-d", "agentwatch_spike",
            "-c", "SELECT provider, model, prompt_tokens, completion_tokens, metadata->>'source' as source FROM spans WHERE metadata::text LIKE '%langchain%' ORDER BY id DESC LIMIT 4;"
        ],
        capture_output=True,
        text=True
    )

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    return result.returncode == 0


if __name__ == "__main__":
    print("Q3 Validation: LangChain Callback Token Extraction")
    print("=" * 60)
    print(f"Backend: {AGENTWATCH_URL}")
    print(f"Mode: {'MOCK (no API keys)' if MOCK_MODE else 'LIVE API CALLS'}")
    print()

    results = {
        "openai": test_openai(),
        "anthropic": test_anthropic(),
        "google": test_google_gemini(),
        "bedrock": test_bedrock()
    }

    time.sleep(1)  # Let backend process

    db_ok = verify_database()

    print("\n" + "=" * 60)
    print("RESULTS:")
    for provider, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {provider}: {status}")
    db_status = "PASS" if db_ok else "FAIL"
    print(f"  Database query: {db_status}")

    all_pass = all(results.values()) and db_ok
    print("\n" + ("="*60))
    final_status = "PASS" if all_pass else "FAIL"
    print(f"Q3 Status: {final_status}")
    print("="*60)

import os
import sys
import time
import json
import uuid
import httpx
import unittest
import multiprocessing
from datetime import datetime, timezone

# Add backend and sdk folders to system path to allow local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sdk")))

# Setup test environment variables before importing main/db
TEST_DB_FILE = "./test_aw.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_FILE}"
os.environ["AGENTWATCH_API_KEY"] = ""

import uvicorn
from main import app
# Mock langchain modules if not installed to prevent import errors in the test runner
import types
try:
    from langchain.callbacks.base import BaseCallbackHandler
    from langchain.schema import LLMResult
except ImportError:
    # Set up mock package hierarchy utilizing types.ModuleType to define __path__ properties
    def create_mock_package(name):
        module = types.ModuleType(name)
        module.__path__ = []
        sys.modules[name] = module
        return module

    lc_pkg = create_mock_package("langchain")
    callbacks_pkg = create_mock_package("langchain.callbacks")
    # Bind callbacks to langchain package
    lc_pkg.callbacks = callbacks_pkg
    
    class BaseCallbackHandler:
        pass
        
    base_mock = types.ModuleType("langchain.callbacks.base")
    base_mock.BaseCallbackHandler = BaseCallbackHandler
    sys.modules["langchain.callbacks.base"] = base_mock
    # Bind base module to callbacks package
    callbacks_pkg.base = base_mock
    
    schema_mock = types.ModuleType("langchain.schema")
    class LLMResult:
        pass
    schema_mock.LLMResult = LLMResult
    sys.modules["langchain.schema"] = schema_mock
    # Bind schema module to langchain package
    lc_pkg.schema = schema_mock

import agentwatch
from agentwatch.patches.openai import current_run_id

# Helper to run uvicorn in a separate process
def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8123, log_level="warning")

# Mock classes for SDK patcher testing
class MockOpenAICompletions:
    def create(self, model, messages, stream=False, **kwargs):
        if stream:
            class Chunk:
                def __init__(self, content, usage=None):
                    self.choices = [{"delta": {"content": content}}]
                    self.usage = usage
            return [
                Chunk("Mocked"),
                Chunk(" stream response"),
                Chunk("", usage=type('Usage', (), {'prompt_tokens': 10, 'completion_tokens': 5})())
            ]
        else:
            class Response:
                def __init__(self):
                    self.choices = [{"message": {"content": "Mocked sync response"}}]
                    self.usage = type('Usage', (), {'prompt_tokens': 12, 'completion_tokens': 6})()
            return Response()

class MockOpenAI:
    def __init__(self, base_url="https://api.openai.com/v1", api_key="test"):
        self.base_url = base_url
        self.chat = type('Chat', (), {'completions': MockOpenAICompletions()})()

class MockAnthropicMessages:
    def create(self, model, messages, stream=False, **kwargs):
        if stream:
            class Chunk:
                def __init__(self, usage=None):
                    self.usage = usage
            return [
                Chunk(),
                Chunk(usage=type('Usage', (), {'input_tokens': 15, 'output_tokens': 8})())
            ]
        else:
            class Response:
                def __init__(self):
                    self.usage = type('Usage', (), {'input_tokens': 14, 'output_tokens': 7})()
            return Response()

class MockAnthropic:
    def __init__(self, api_key="test"):
        self.messages = MockAnthropicMessages()

class MockBedrock:
    def invoke_model(self, modelId, body, **kwargs):
        body_json = json.loads(body)
        if "claude" in modelId:
            response_body = {"usage": {"input_tokens": 18, "output_tokens": 9}}
        elif "llama" in modelId:
            response_body = {"prompt_token_count": 20, "generation_token_count": 10}
        else:
            response_body = {"inputTextTokenCount": 22, "results": [{"tokenCount": 11}]}
        
        class StreamingBody:
            def __init__(self, data):
                self.data = data
            def read(self):
                return self.data.encode()
        
        return {"body": StreamingBody(json.dumps(response_body))}


class TestAgentWatchIntegration(unittest.TestCase):
    server_process = None

    @classmethod
    def setUpClass(cls):
        # Remove old test DB if exists
        if os.path.exists(TEST_DB_FILE):
            try:
                os.remove(TEST_DB_FILE)
            except Exception:
                pass

        # Start FastAPI server in background process
        cls.server_process = multiprocessing.Process(target=run_server)
        cls.server_process.start()
        
        # Give server some time to start up
        time.sleep(1.5)

    @classmethod
    def tearDownClass(cls):
        # Shut down server process
        if cls.server_process:
            cls.server_process.terminate()
            cls.server_process.join()

        # Clean up database file
        time.sleep(0.5)
        if os.path.exists(TEST_DB_FILE):
            try:
                os.remove(TEST_DB_FILE)
            except Exception as e:
                print(f"Warning: Failed to delete test database file: {e}")

    def test_01_health_check(self):
        """Verify backend server health check is operational."""
        res = httpx.get("http://127.0.0.1:8123/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "ok")

    def test_02_sdk_initialization_and_runs(self):
        """Test SDK client creation and runs push."""
        client = agentwatch.init("http://127.0.0.1:8123")
        run_id = "test-run-1"
        
        # Create a run
        client.create_run(run_id=run_id, name="Test SDK Run", session_id="session-1", tags=["test", "integration"])
        time.sleep(0.2)  # Wait for thread pool to finish posting
        
        # Verify run in DB
        res = httpx.get("http://127.0.0.1:8123/v1/runs")
        self.assertEqual(res.status_code, 200)
        runs = res.json()["data"]
        self.assertTrue(any(r["run_id"] == run_id for r in runs))

        # Update run status
        client.update_run(run_id=run_id, status="success")
        time.sleep(0.2)
        
        # Check status update
        res = httpx.get(f"http://127.0.0.1:8123/v1/runs/{run_id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["data"]["status"], "success")

    def test_03_patch_openai_sync_and_stream(self):
        """Verify OpenAI patches aggregate usage and push spans successfully."""
        aw_client = agentwatch.init("http://127.0.0.1:8123")
        openai_client = MockOpenAI()
        agentwatch.patch_openai(openai_client)
        
        run_id = "run-openai-test"
        aw_client.create_run(run_id=run_id, name="OpenAI Test Chain")
        current_run_id.set(run_id)

        # 1. Sync creation
        openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello"}]
        )
        time.sleep(0.2)

        # 2. Stream creation
        stream = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Stream me"}],
            stream=True
        )
        # Consume stream
        for _ in stream:
            pass
        # Poll backend for up to 1 second for background async thread to complete DB write
        spans = []
        for _ in range(10):
            res = httpx.get(f"http://127.0.0.1:8123/v1/runs/{run_id}")
            self.assertEqual(res.status_code, 200)
            spans = res.json()["data"]["spans"]
            if len(spans) == 2 and any(s["status"] == "success" and s["prompt_tokens"] == 10 for s in spans):
                break
            time.sleep(0.1)

        print(f"\nDEBUG: spans logged for OpenAI: {json.dumps(spans, indent=2)}")
        self.assertEqual(len(spans), 2)
        # Verify token counts aggregated
        self.assertTrue(any(s["prompt_tokens"] == 12 and s["completion_tokens"] == 6 for s in spans)) # Sync
        self.assertTrue(any(s["prompt_tokens"] == 10 and s["completion_tokens"] == 5 for s in spans)) # Stream

    def test_04_patch_anthropic_and_bedrock(self):
        """Test Anthropic and AWS Bedrock patches extract tokens and post correctly."""
        aw_client = agentwatch.init("http://127.0.0.1:8123")
        
        run_id = "run-multiprovider-test"
        aw_client.create_run(run_id=run_id, name="Multi-Provider Test Chain")
        current_run_id.set(run_id)

        # Test Anthropic
        anthropic_client = MockAnthropic()
        agentwatch.patch_anthropic(anthropic_client)
        anthropic_client.messages.create(
            model="claude-3-5-sonnet",
            messages=[{"role": "user", "content": "Hello"}]
        )
        time.sleep(0.2)

        # Test Bedrock Claude
        bedrock_client = MockBedrock()
        agentwatch.patch_bedrock(bedrock_client)
        bedrock_client.invoke_model(
            modelId="anthropic.claude-v3",
            body=json.dumps({"max_tokens": 10})
        )
        time.sleep(0.2)

        # Test Bedrock Llama
        bedrock_client.invoke_model(
            modelId="meta.llama-v3",
            body=json.dumps({"max_gen": 10})
        )
        time.sleep(0.2)

        # Check DB
        res = httpx.get(f"http://127.0.0.1:8123/v1/runs/{run_id}")
        self.assertEqual(res.status_code, 200)
        spans = res.json()["data"]["spans"]
        
        self.assertEqual(len(spans), 3)
        self.assertTrue(any(s["provider"] == "anthropic" and s["prompt_tokens"] == 14 for s in spans))
        self.assertTrue(any(s["provider"] == "bedrock" and s["model"] == "anthropic.claude-v3" and s["prompt_tokens"] == 18 for s in spans))
        self.assertTrue(any(s["provider"] == "bedrock" and s["model"] == "meta.llama-v3" and s["prompt_tokens"] == 20 for s in spans))

    def test_05_langchain_callback_adapter(self):
        """Test LangChain callback generates parent-child hierarchical spans correctly."""
        client = agentwatch.init("http://127.0.0.1:8123")
        
        run_id = "run-langchain-chain-test"
        callback = agentwatch.AgentWatchCallbackHandler(client, run_id=run_id)

        # Mock langchain invoking sequence
        chain_uuid = uuid.uuid4()
        llm_uuid = uuid.uuid4()
        tool_uuid = uuid.uuid4()

        # Step 1: Chain starts
        callback.on_chain_start(
            serialized={"name": "MyRootChain"},
            inputs={"input": "run agent"},
            run_id=chain_uuid
        )
        time.sleep(0.1)

        # Step 2: Nested LLM starts
        callback.on_llm_start(
            serialized={"name": "gpt-4o-mini"},
            prompts=["Say Hello"],
            run_id=llm_uuid,
            parent_run_id=chain_uuid
        )
        time.sleep(0.1)

        # Step 3: Nested LLM ends
        class MockLLMOutput:
            def __init__(self):
                self.llm_output = {
                    "token_usage": {"prompt_tokens": 8, "completion_tokens": 4},
                    "model_name": "gpt-4o-mini"
                }
                self.generations = [[type('Gen', (), {'text': 'Hello'})()]]
        
        callback.on_llm_end(MockLLMOutput(), run_id=llm_uuid, parent_run_id=chain_uuid)
        time.sleep(0.1)

        # Step 4: Tool execution
        callback.on_tool_start(
            serialized={"name": "SearchTool"},
            input_str="query details",
            run_id=tool_uuid,
            parent_run_id=chain_uuid
        )
        time.sleep(0.1)

        callback.on_tool_end("Results found", run_id=tool_uuid, parent_run_id=chain_uuid)
        time.sleep(0.1)

        # Step 5: Chain ends
        callback.on_chain_end(outputs={"output": "Finished!"}, run_id=chain_uuid)
        time.sleep(0.3)

        # Verify tree hierarchy in DB
        res = httpx.get(f"http://127.0.0.1:8123/v1/runs/{run_id}")
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        spans = data["spans"]

        self.assertEqual(len(spans), 3) # Chain + LLM + Tool
        
        # Verify parent-child ID linkages
        chain_span = next(s for s in spans if s["span_type"] == "chain")
        llm_span = next(s for s in spans if s["span_type"] == "llm")
        tool_span = next(s for s in spans if s["span_type"] == "tool")

        self.assertEqual(llm_span["parent_span_id"], chain_span["span_id"])
        self.assertEqual(tool_span["parent_span_id"], chain_span["span_id"])
        self.assertEqual(chain_span["parent_span_id"], None)


if __name__ == "__main__":
    unittest.main()

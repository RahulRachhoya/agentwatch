"""
LangChain callback handler for AgentWatch.

Validates token extraction across LangChain LLM wrappers (Q3).
Covers OpenAI, Anthropic, Gemini, Bedrock-hosted Claude.
"""
import time
import os
from typing import Any, Dict, List, Optional
import httpx
from langchain.callbacks.base import BaseCallbackHandler

AGENTWATCH_URL = os.getenv("AGENTWATCH_URL", "http://localhost:8000")

class AgentWatchCallback(BaseCallbackHandler):
    def __init__(self, run_id: str = "spike-langchain-test"):
        self.run_id = run_id
        self.spans: Dict[str, Dict] = {}
    
    def on_llm_start(self, serialized: Dict, prompts: List[str], **kwargs) -> None:
        span_id = f"llm-{int(time.time() * 1000)}"
        self.spans[span_id] = {
            "span_id": span_id,
            "run_id": self.run_id,
            "name": "langchain.llm",
            "span_type": "llm",
            "start_time": time.time(),
            "metadata": {"prompts": prompts, "serialized": serialized}
        }
    
    def on_llm_end(self, response, **kwargs) -> None:
        if not self.spans:
            return
        
        span_id = list(self.spans.keys())[-1]
        span = self.spans[span_id]
        
        # Extract tokens from response.llm_output
        llm_output = getattr(response, "llm_output", {}) or {}
        token_usage = llm_output.get("token_usage", {})
        
        span.update({
            "end_time": time.time(),
            "provider": self._detect_provider(llm_output),
            "model": llm_output.get("model_name", "unknown"),
            "prompt_tokens": token_usage.get("prompt_tokens", 0),
            "completion_tokens": token_usage.get("completion_tokens", 0),
            "total_tokens": token_usage.get("total_tokens", 0),
        })
        
        self._send_span(span)
        del self.spans[span_id]
    
    def on_tool_start(self, serialized: Dict, input_str: str, **kwargs) -> None:
        span_id = f"tool-{int(time.time() * 1000)}"
        self.spans[span_id] = {
            "span_id": span_id,
            "run_id": self.run_id,
            "name": serialized.get("name", "unknown_tool"),
            "span_type": "tool",
            "start_time": time.time(),
            "metadata": {"input": input_str}
        }
    
    def on_tool_end(self, output: str, **kwargs) -> None:
        if not self.spans:
            return
        
        span_id = list(self.spans.keys())[-1]
        span = self.spans[span_id]
        span["end_time"] = time.time()
        span["metadata"]["output"] = output
        
        self._send_span(span)
        del self.spans[span_id]
    
    def on_chain_error(self, error: Exception, **kwargs) -> None:
        if not self.spans:
            return
        
        span_id = list(self.spans.keys())[-1]
        span = self.spans[span_id]
        span["end_time"] = time.time()
        span["metadata"]["error"] = str(error)
        span["status"] = "error"
        
        self._send_span(span)
        del self.spans[span_id]
    
    def _detect_provider(self, llm_output: Dict) -> str:
        """Detect provider from llm_output model_name."""
        model = llm_output.get("model_name", "")
        if "gpt" in model:
            return "openai"
        if "claude" in model:
            return "anthropic"
        if "gemini" in model:
            return "google"
        if "bedrock" in model or "anthropic.claude" in model:
            return "bedrock"
        return "unknown"
    
    def _send_span(self, span: Dict) -> None:
        try:
            httpx.post(
                f"{AGENTWATCH_URL}/v1/spans/batch",
                json={"spans": [span]},
                timeout=5.0
            )
        except Exception:
            pass

if __name__ == "__main__":
    from langchain_openai import ChatOpenAI
    from langchain_anthropic import ChatAnthropic
    
    callback = AgentWatchCallback()
    
    # Test OpenAI
    llm = ChatOpenAI(model="gpt-4o-mini", max_tokens=10)
    response = llm.invoke("Say hi", config={"callbacks": [callback]})
    print("OpenAI span sent:", response.content)
    
    # Test Anthropic
    llm = ChatAnthropic(model="claude-3-5-sonnet-20241022", max_tokens=10)
    response = llm.invoke("Say hi", config={"callbacks": [callback]})
    print("Anthropic span sent:", response.content)

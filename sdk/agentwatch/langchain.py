import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import LLMResult

from agentwatch.client import AgentWatchClient

logger = logging.getLogger("agentwatch.langchain")

class AgentWatchCallbackHandler(BaseCallbackHandler):
    """
    LangChain Callback Handler that auto-records chains, agent executions, 
    LLM generation metrics, and tools executions to AgentWatch.
    """
    
    def __init__(self, client: AgentWatchClient, run_id: Optional[str] = None, session_id: Optional[str] = None):
        super().__init__()
        self.client = client
        self.custom_run_id = run_id
        self.session_id = session_id
        # Map trace step UUIDs to top-level run_id strings
        self.trace_run_ids: Dict[UUID, str] = {}

    def _get_run_id(self, run_id: UUID, parent_run_id: Optional[UUID]) -> str:
        """Dynamically resolve or generate top-level run_id for hierarchical traces."""
        if self.custom_run_id:
            return self.custom_run_id
        
        # If it has a parent in execution tree, inherit the top-level run ID
        if parent_run_id and parent_run_id in self.trace_run_ids:
            run_str = self.trace_run_ids[parent_run_id]
            self.trace_run_ids[run_id] = run_str
            return run_str
            
        # Otherwise, this is a root node. Create a new run_id.
        run_str = f"run_{run_id.hex[:12]}"
        self.trace_run_ids[run_id] = run_str
        return run_str

    def on_chain_start(
        self, serialized: Dict[str, Any], inputs: Dict[str, Any], *, 
        run_id: UUID, parent_run_id: Optional[UUID] = None, 
        tags: Optional[List[str]] = None, metadata: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> None:
        top_run_id = self._get_run_id(run_id, parent_run_id)
        name = serialized.get("name") or serialized.get("id", ["Chain"])[-1]
        
        if not parent_run_id:
            # Root chain starting - register the top-level Run
            self.client.create_run(
                run_id=top_run_id,
                name=name,
                session_id=self.session_id,
                tags=tags or [],
                metadata=metadata or {}
            )
            
        span = {
            "span_id": str(run_id),
            "run_id": top_run_id,
            "parent_span_id": str(parent_run_id) if parent_run_id else None,
            "span_type": "chain",
            "name": name,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "status": "running",
            "metadata": {"inputs": inputs, "serialized": serialized, **(metadata or {})}
        }
        self.client.send_spans([span])

    def on_chain_end(
        self, outputs: Dict[str, Any], *, 
        run_id: UUID, parent_run_id: Optional[UUID] = None, **kwargs: Any
    ) -> None:
        top_run_id = self.trace_run_ids.get(run_id) or self.custom_run_id
        if not top_run_id:
            return
            
        span = {
            "span_id": str(run_id),
            "run_id": top_run_id,
            "started_at": datetime.now(timezone.utc).isoformat(),  # Server updates ended_at on conflict
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "span_type": "chain",
            "name": "langchain.chain",
            "status": "success",
            "metadata": {"outputs": outputs}
        }
        self.client.send_spans([span])
        
        if not parent_run_id:
            self.client.update_run(run_id=top_run_id, status="success")

    def on_chain_error(
        self, error: BaseException, *, 
        run_id: UUID, parent_run_id: Optional[UUID] = None, **kwargs: Any
    ) -> None:
        top_run_id = self.trace_run_ids.get(run_id) or self.custom_run_id
        if not top_run_id:
            return
            
        span = {
            "span_id": str(run_id),
            "run_id": top_run_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "span_type": "chain",
            "name": "langchain.chain",
            "status": "error",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "metadata": {}
        }
        self.client.send_spans([span])
        
        if not parent_run_id:
            self.client.update_run(run_id=top_run_id, status="error", error_message=str(error))

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], *, 
        run_id: UUID, parent_run_id: Optional[UUID] = None, 
        tags: Optional[List[str]] = None, metadata: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> None:
        top_run_id = self._get_run_id(run_id, parent_run_id)
        name = serialized.get("name") or serialized.get("id", ["LLM"])[-1]
        
        if not parent_run_id:
            self.client.create_run(
                run_id=top_run_id,
                name=name,
                session_id=self.session_id,
                tags=tags or [],
                metadata=metadata or {}
            )

        span = {
            "span_id": str(run_id),
            "run_id": top_run_id,
            "parent_span_id": str(parent_run_id) if parent_run_id else None,
            "span_type": "llm",
            "name": name,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "status": "running",
            "metadata": {"prompts": prompts, "serialized": serialized, **(metadata or {})}
        }
        self.client.send_spans([span])

    def on_llm_end(
        self, response: LLMResult, *, 
        run_id: UUID, parent_run_id: Optional[UUID] = None, **kwargs: Any
    ) -> None:
        top_run_id = self.trace_run_ids.get(run_id) or self.custom_run_id
        if not top_run_id:
            return
            
        llm_output = response.llm_output or {}
        token_usage = llm_output.get("token_usage", {}) or {}
        model_name = llm_output.get("model_name", "unknown")
        
        # Simple provider detection
        provider = "unknown"
        model_lower = model_name.lower()
        if "gpt" in model_lower:
            provider = "openai"
        elif "claude" in model_lower:
            provider = "anthropic"
        elif "gemini" in model_lower:
            provider = "google"
        elif "bedrock" in model_lower or "anthropic.claude" in model_lower:
            provider = "bedrock"

        # Try to capture preview texts
        input_preview = None
        output_preview = None
        try:
            if response.generations and response.generations[0]:
                output_preview = response.generations[0][0].text[:500]
        except Exception:
            pass

        span = {
            "span_id": str(run_id),
            "run_id": top_run_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "span_type": "llm",
            "name": f"langchain.{model_name}",
            "model": model_name,
            "provider": provider,
            "prompt_tokens": token_usage.get("prompt_tokens", 0) or 0,
            "completion_tokens": token_usage.get("completion_tokens", 0) or 0,
            "output_preview": output_preview,
            "status": "success",
            "metadata": {"llm_output": llm_output}
        }
        self.client.send_spans([span])
        
        if not parent_run_id:
            self.client.update_run(run_id=top_run_id, status="success")

    def on_llm_error(
        self, error: BaseException, *, 
        run_id: UUID, parent_run_id: Optional[UUID] = None, **kwargs: Any
    ) -> None:
        top_run_id = self.trace_run_ids.get(run_id) or self.custom_run_id
        if not top_run_id:
            return
            
        span = {
            "span_id": str(run_id),
            "run_id": top_run_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "span_type": "llm",
            "name": "langchain.llm",
            "status": "error",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "metadata": {}
        }
        self.client.send_spans([span])
        
        if not parent_run_id:
            self.client.update_run(run_id=top_run_id, status="error", error_message=str(error))

    def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, *, 
        run_id: UUID, parent_run_id: Optional[UUID] = None, 
        tags: Optional[List[str]] = None, metadata: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> None:
        top_run_id = self._get_run_id(run_id, parent_run_id)
        name = serialized.get("name") or "tool"

        span = {
            "span_id": str(run_id),
            "run_id": top_run_id,
            "parent_span_id": str(parent_run_id) if parent_run_id else None,
            "span_type": "tool",
            "name": name,
            "tool_name": name,
            "tool_input": {"input": input_str},
            "started_at": datetime.now(timezone.utc).isoformat(),
            "status": "running",
            "metadata": {"serialized": serialized, **(metadata or {})}
        }
        self.client.send_spans([span])

    def on_tool_end(
        self, output: str, *, 
        run_id: UUID, parent_run_id: Optional[UUID] = None, **kwargs: Any
    ) -> None:
        top_run_id = self.trace_run_ids.get(run_id) or self.custom_run_id
        if not top_run_id:
            return
            
        span = {
            "span_id": str(run_id),
            "run_id": top_run_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "span_type": "tool",
            "name": "langchain.tool",
            "status": "success",
            "tool_output": {"output": output},
            "metadata": {}
        }
        self.client.send_spans([span])

    def on_tool_error(
        self, error: BaseException, *, 
        run_id: UUID, parent_run_id: Optional[UUID] = None, **kwargs: Any
    ) -> None:
        top_run_id = self.trace_run_ids.get(run_id) or self.custom_run_id
        if not top_run_id:
            return
            
        span = {
            "span_id": str(run_id),
            "run_id": top_run_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "span_type": "tool",
            "name": "langchain.tool",
            "status": "error",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "metadata": {}
        }
        self.client.send_spans([span])

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from contextvars import ContextVar

from agentwatch.client import AgentWatchClient

# Context variable to auto-link model invocations to a parent run context
current_run_id: ContextVar[Optional[str]] = ContextVar("current_run_id", default=None)

def send_running_span(aw_client: AgentWatchClient, run_id: str, span_id: str, model: str, provider: str, started_at: datetime):
    span = {
        "span_id": span_id,
        "run_id": run_id,
        "span_type": "llm",
        "name": f"{provider}.{model}",
        "model": model,
        "provider": provider,
        "started_at": started_at.isoformat(),
        "status": "running",
        "metadata": {"source": "native"}
    }
    aw_client.send_spans([span])

def send_completed_span(
    aw_client: AgentWatchClient, run_id: str, span_id: str, model: str, provider: str, 
    started_at: datetime, prompt_tokens: int, completion_tokens: int
):
    ended_at = datetime.now(timezone.utc)
    span = {
        "span_id": span_id,
        "run_id": run_id,
        "span_type": "llm",
        "name": f"{provider}.{model}",
        "model": model,
        "provider": provider,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "started_at": started_at.isoformat(),
        "ended_at": ended_at.isoformat(),
        "status": "success",
        "metadata": {"source": "native"}
    }
    aw_client.send_spans([span])

def send_error_span(aw_client: AgentWatchClient, run_id: str, span_id: str, model: str, provider: str, started_at: datetime, exception: Exception):
    ended_at = datetime.now(timezone.utc)
    span = {
        "span_id": span_id,
        "run_id": run_id,
        "span_type": "llm",
        "name": f"{provider}.{model}",
        "model": model,
        "provider": provider,
        "started_at": started_at.isoformat(),
        "ended_at": ended_at.isoformat(),
        "status": "error",
        "error_type": type(exception).__name__,
        "error_message": str(exception),
        "metadata": {"source": "native"}
    }
    aw_client.send_spans([span])

def patch_openai(client: Any, aw_client: AgentWatchClient, provider: Optional[str] = None):
    """
    Instrument sync or async OpenAI client's chat.completions.create calls to auto-log spans.
    """
    is_async = hasattr(client, "_is_async") and client._is_async or "Async" in type(client).__name__
    
    # Resolve provider
    client_base_url = str(client.base_url)
    detected_provider = "openai"
    if provider:
        detected_provider = provider
    elif "deepseek.com" in client_base_url:
        detected_provider = "deepseek"
    elif "moonshot.cn" in client_base_url:
        detected_provider = "moonshot"

    original_create = client.chat.completions.create

    if is_async:
        async def tracked_create_async(*args, **kwargs):
            start_time = datetime.now(timezone.utc)
            
            # Extract run context details
            run_id = (
                kwargs.pop("run_id", None) or 
                kwargs.get("extra_headers", {}).get("x-run-id") or 
                current_run_id.get() or 
                f"run_{uuid.uuid4().hex[:12]}"
            )
            span_id = f"span_{uuid.uuid4().hex[:12]}"
            model = kwargs.get("model", "unknown")
            
            is_stream = kwargs.get("stream", False)
            if is_stream:
                if "stream_options" not in kwargs:
                    kwargs["stream_options"] = {"include_usage": True}
            
            send_running_span(aw_client, run_id, span_id, model, detected_provider, start_time)

            try:
                response = await original_create(*args, **kwargs)
            except Exception as e:
                send_error_span(aw_client, run_id, span_id, model, detected_provider, start_time, e)
                raise e

            if is_stream:
                async def async_stream_generator():
                    chunks = []
                    usage = None
                    try:
                        async for chunk in response:
                            chunks.append(chunk)
                            if hasattr(chunk, "usage") and chunk.usage:
                                usage = chunk.usage
                            yield chunk
                    except Exception as stream_err:
                        send_error_span(aw_client, run_id, span_id, model, detected_provider, start_time, stream_err)
                        raise stream_err
                    
                    prompt_tokens = usage.prompt_tokens if usage else 0
                    completion_tokens = usage.completion_tokens if usage else 0
                    send_completed_span(
                        aw_client, run_id, span_id, model, detected_provider, 
                        start_time, prompt_tokens, completion_tokens
                    )
                return async_stream_generator()
            else:
                usage = getattr(response, "usage", None)
                prompt_tokens = usage.prompt_tokens if usage else 0
                completion_tokens = usage.completion_tokens if usage else 0
                send_completed_span(
                    aw_client, run_id, span_id, model, detected_provider, 
                    start_time, prompt_tokens, completion_tokens
                )
                return response

        client.chat.completions.create = tracked_create_async
    else:
        def tracked_create(*args, **kwargs):
            start_time = datetime.now(timezone.utc)
            
            run_id = (
                kwargs.pop("run_id", None) or 
                kwargs.get("extra_headers", {}).get("x-run-id") or 
                current_run_id.get() or 
                f"run_{uuid.uuid4().hex[:12]}"
            )
            span_id = f"span_{uuid.uuid4().hex[:12]}"
            model = kwargs.get("model", "unknown")
            
            is_stream = kwargs.get("stream", False)
            if is_stream:
                if "stream_options" not in kwargs:
                    kwargs["stream_options"] = {"include_usage": True}
            
            send_running_span(aw_client, run_id, span_id, model, detected_provider, start_time)

            try:
                response = original_create(*args, **kwargs)
            except Exception as e:
                send_error_span(aw_client, run_id, span_id, model, detected_provider, start_time, e)
                raise e

            if is_stream:
                def stream_generator():
                    chunks = []
                    usage = None
                    try:
                        for chunk in response:
                            chunks.append(chunk)
                            if hasattr(chunk, "usage") and chunk.usage:
                                usage = chunk.usage
                            yield chunk
                    except Exception as stream_err:
                        send_error_span(aw_client, run_id, span_id, model, detected_provider, start_time, stream_err)
                        raise stream_err
                    
                    prompt_tokens = usage.prompt_tokens if usage else 0
                    completion_tokens = usage.completion_tokens if usage else 0
                    send_completed_span(
                        aw_client, run_id, span_id, model, detected_provider, 
                        start_time, prompt_tokens, completion_tokens
                    )
                return stream_generator()
            else:
                usage = getattr(response, "usage", None)
                prompt_tokens = usage.prompt_tokens if usage else 0
                completion_tokens = usage.completion_tokens if usage else 0
                send_completed_span(
                    aw_client, run_id, span_id, model, detected_provider, 
                    start_time, prompt_tokens, completion_tokens
                )
                return response

        client.chat.completions.create = tracked_create

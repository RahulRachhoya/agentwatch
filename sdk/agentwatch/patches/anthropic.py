import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from agentwatch.client import AgentWatchClient
from agentwatch.patches.openai import current_run_id

def send_running_span(aw_client: AgentWatchClient, run_id: str, span_id: str, model: str, started_at: datetime):
    span = {
        "span_id": span_id,
        "run_id": run_id,
        "span_type": "llm",
        "name": f"anthropic.{model}",
        "model": model,
        "provider": "anthropic",
        "started_at": started_at.isoformat(),
        "status": "running",
        "metadata": {"source": "native"}
    }
    aw_client.send_spans([span])

def send_completed_span(
    aw_client: AgentWatchClient, run_id: str, span_id: str, model: str, 
    started_at: datetime, input_tokens: int, output_tokens: int
):
    ended_at = datetime.now(timezone.utc)
    span = {
        "span_id": span_id,
        "run_id": run_id,
        "span_type": "llm",
        "name": f"anthropic.{model}",
        "model": model,
        "provider": "anthropic",
        "prompt_tokens": input_tokens,
        "completion_tokens": output_tokens,
        "started_at": started_at.isoformat(),
        "ended_at": ended_at.isoformat(),
        "status": "success",
        "metadata": {"source": "native"}
    }
    aw_client.send_spans([span])

def send_error_span(aw_client: AgentWatchClient, run_id: str, span_id: str, model: str, started_at: datetime, exception: Exception):
    ended_at = datetime.now(timezone.utc)
    span = {
        "span_id": span_id,
        "run_id": run_id,
        "span_type": "llm",
        "name": f"anthropic.{model}",
        "model": model,
        "provider": "anthropic",
        "started_at": started_at.isoformat(),
        "ended_at": ended_at.isoformat(),
        "status": "error",
        "error_type": type(exception).__name__,
        "error_message": str(exception),
        "metadata": {"source": "native"}
    }
    aw_client.send_spans([span])

def patch_anthropic(client: Any, aw_client: AgentWatchClient):
    """Instrument sync or async Anthropic client messages.create calls."""
    is_async = hasattr(client, "_is_async") and client._is_async or "Async" in type(client).__name__
    original_create = client.messages.create

    if is_async:
        async def tracked_create_async(*args, **kwargs):
            start_time = datetime.now(timezone.utc)
            run_id = (
                kwargs.pop("run_id", None) or 
                current_run_id.get() or 
                f"run_{uuid.uuid4().hex[:12]}"
            )
            span_id = f"span_{uuid.uuid4().hex[:12]}"
            model = kwargs.get("model", "unknown")
            is_stream = kwargs.get("stream", False)

            send_running_span(aw_client, run_id, span_id, model, start_time)

            try:
                response = await original_create(*args, **kwargs)
            except Exception as e:
                send_error_span(aw_client, run_id, span_id, model, start_time, e)
                raise e

            if is_stream:
                async def async_stream_generator():
                    usage = None
                    try:
                        async for chunk in response:
                            if hasattr(chunk, "message") and hasattr(chunk.message, "usage") and chunk.message.usage:
                                usage = chunk.message.usage
                            elif hasattr(chunk, "usage") and chunk.usage:
                                usage = chunk.usage
                            yield chunk
                    except Exception as stream_err:
                        send_error_span(aw_client, run_id, span_id, model, start_time, stream_err)
                        raise stream_err
                    
                    input_tokens = usage.input_tokens if usage else 0
                    output_tokens = usage.output_tokens if usage else 0
                    send_completed_span(aw_client, run_id, span_id, model, start_time, input_tokens, output_tokens)
                return async_stream_generator()
            else:
                usage = getattr(response, "usage", None)
                input_tokens = usage.input_tokens if usage else 0
                output_tokens = usage.output_tokens if usage else 0
                send_completed_span(aw_client, run_id, span_id, model, start_time, input_tokens, output_tokens)
                return response

        client.messages.create = tracked_create_async
    else:
        def tracked_create(*args, **kwargs):
            start_time = datetime.now(timezone.utc)
            run_id = (
                kwargs.pop("run_id", None) or 
                current_run_id.get() or 
                f"run_{uuid.uuid4().hex[:12]}"
            )
            span_id = f"span_{uuid.uuid4().hex[:12]}"
            model = kwargs.get("model", "unknown")
            is_stream = kwargs.get("stream", False)

            send_running_span(aw_client, run_id, span_id, model, start_time)

            try:
                response = original_create(*args, **kwargs)
            except Exception as e:
                send_error_span(aw_client, run_id, span_id, model, start_time, e)
                raise e

            if is_stream:
                def stream_generator():
                    usage = None
                    try:
                        for chunk in response:
                            if hasattr(chunk, "message") and hasattr(chunk.message, "usage") and chunk.message.usage:
                                usage = chunk.message.usage
                            elif hasattr(chunk, "usage") and chunk.usage:
                                usage = chunk.usage
                            yield chunk
                    except Exception as stream_err:
                        send_error_span(aw_client, run_id, span_id, model, start_time, stream_err)
                        raise stream_err
                    
                    input_tokens = usage.input_tokens if usage else 0
                    output_tokens = usage.output_tokens if usage else 0
                    send_completed_span(aw_client, run_id, span_id, model, start_time, input_tokens, output_tokens)
                return stream_generator()
            else:
                usage = getattr(response, "usage", None)
                input_tokens = usage.input_tokens if usage else 0
                output_tokens = usage.output_tokens if usage else 0
                send_completed_span(aw_client, run_id, span_id, model, start_time, input_tokens, output_tokens)
                return response

        client.messages.create = tracked_create

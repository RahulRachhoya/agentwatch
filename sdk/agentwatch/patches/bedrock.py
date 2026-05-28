import io
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from agentwatch.client import AgentWatchClient
from agentwatch.patches.openai import current_run_id

logger = logging.getLogger("agentwatch.bedrock")

# Extensible model-family token extractors registry
TOKEN_EXTRACTORS = {
    "anthropic.claude": lambda body: {
        "prompt_tokens": body.get("usage", {}).get("input_tokens", 0),
        "completion_tokens": body.get("usage", {}).get("output_tokens", 0),
    },
    "meta.llama": lambda body: {
        "prompt_tokens": body.get("prompt_token_count", 0),
        "completion_tokens": body.get("generation_token_count", 0),
    },
    "amazon.titan": lambda body: {
        "prompt_tokens": body.get("inputTextTokenCount", 0),
        "completion_tokens": body.get("results", [{}])[0].get("tokenCount", 0),
    },
    "cohere.command": lambda body: {
        "prompt_tokens": body.get("prompt_token_count", 0), # Estimated based on Cohere Bedrock output shapes
        "completion_tokens": body.get("response", {}).get("token_count", 0),
    }
}

def _detect_model_family(model_id: str) -> str:
    """Detect model family from AWS Bedrock model IDs."""
    if model_id.startswith("anthropic.claude"):
        return "anthropic.claude"
    elif model_id.startswith("meta.llama"):
        return "meta.llama"
    elif model_id.startswith("amazon.titan"):
        return "amazon.titan"
    elif model_id.startswith("cohere.command"):
        return "cohere.command"
    return "unknown"

class RereadableBody:
    """Wrapper around botocore StreamingBody to allow duplicate read calls."""
    def __init__(self, data: bytes):
        self._raw_data = data
        self._stream = io.BytesIO(data)

    def read(self, amt=None):
        return self._stream.read(amt)

    def close(self):
        self._stream.close()

def send_span(
    aw_client: AgentWatchClient, run_id: str, span_id: str, model: str, 
    started_at: datetime, prompt_tokens: int, completion_tokens: int, status: str, 
    error_message: Optional[str] = None
):
    ended_at = datetime.now(timezone.utc)
    span = {
        "span_id": span_id,
        "run_id": run_id,
        "span_type": "llm",
        "name": f"bedrock.{model}",
        "model": model,
        "provider": "bedrock",
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "started_at": started_at.isoformat(),
        "ended_at": ended_at.isoformat(),
        "status": status,
        "error_message": error_message,
        "metadata": {"source": "native"}
    }
    aw_client.send_spans([span])

def patch_bedrock(client: Any, aw_client: AgentWatchClient):
    """Instrument boto3 bedrock-runtime invoke_model requests."""
    original_invoke = client.invoke_model

    def tracked_invoke(*args, **kwargs):
        start_time = datetime.now(timezone.utc)
        run_id = (
            kwargs.pop("run_id", None) or 
            current_run_id.get() or 
            f"run_{uuid.uuid4().hex[:12]}"
        )
        span_id = f"span_{uuid.uuid4().hex[:12]}"
        model_id = kwargs.get("modelId", "unknown")

        try:
            response = original_invoke(*args, **kwargs)
        except Exception as e:
            send_span(
                aw_client, run_id, span_id, model_id, start_time, 
                0, 0, "error", error_message=str(e)
            )
            raise e

        try:
            # Read and replace the streaming body with rereadable wrapper
            raw_body = response["body"].read()
            response["body"] = RereadableBody(raw_body)

            body_str = raw_body.decode("utf-8")
            body_json = json.loads(body_str)

            # Extract tokens
            family = _detect_model_family(model_id)
            extractor = TOKEN_EXTRACTORS.get(family)
            if extractor:
                tokens = extractor(body_json)
                prompt_tokens = tokens.get("prompt_tokens", 0)
                completion_tokens = tokens.get("completion_tokens", 0)
            else:
                prompt_tokens, completion_tokens = 0, 0
                
            send_span(
                aw_client, run_id, span_id, model_id, start_time, 
                prompt_tokens, completion_tokens, "success"
            )
        except Exception as parse_err:
            logger.warning(f"Failed to parse Bedrock response tokens: {parse_err}")
            # Still record success span with 0 tokens if inference succeeded
            send_span(
                aw_client, run_id, span_id, model_id, start_time, 
                0, 0, "success"
            )
            
        return response

    client.invoke_model = tracked_invoke

"""
Bedrock SDK auto-instrumentation.

Wraps boto3 bedrock-runtime invoke_model calls.
Token extraction is per-model-family — Claude, Llama, Titan each return different response shapes.
"""
import json
import time
import os
import httpx

AGENTWATCH_URL = os.getenv("AGENTWATCH_URL", "http://localhost:8000")

# Model-family-specific token extractors
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
}

def _detect_model_family(model_id: str) -> str:
    """anthropic.claude-3-5-sonnet-20241022-v2:0 -> anthropic.claude"""
    if model_id.startswith("anthropic.claude"):
        return "anthropic.claude"
    if model_id.startswith("meta.llama"):
        return "meta.llama"
    if model_id.startswith("amazon.titan"):
        return "amazon.titan"
    return "unknown"

def send_span(model: str, prompt_tokens: int, completion_tokens: int, duration_ms: int):
    try:
        httpx.post(
            f"{AGENTWATCH_URL}/v1/spans/batch",
            json={
                "spans": [{
                    "span_id": f"bedrock-{int(time.time() * 1000)}",
                    "run_id": "spike-bedrock-test",
                    "name": "bedrock.invoke_model",
                    "span_type": "llm",
                    "start_time": time.time() - (duration_ms / 1000),
                    "end_time": time.time(),
                    "provider": "bedrock",
                    "model": model,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                    "metadata": {"source": "bedrock_patch"}
                }]
            },
            timeout=5.0
        )
    except Exception:
        pass

def install(client):
    """Patch boto3 bedrock-runtime client."""
    original_invoke = client.invoke_model
    
    def tracked_invoke(*args, **kwargs):
        start = time.time()
        response = original_invoke(*args, **kwargs)
        
        model_id = kwargs.get("modelId", "unknown")
        body = json.loads(response["body"].read())
        response["body"] = type("BytesIO", (), {"read": lambda: json.dumps(body).encode()})()
        
        family = _detect_model_family(model_id)
        extractor = TOKEN_EXTRACTORS.get(family, lambda _: {"prompt_tokens": 0, "completion_tokens": 0})
        tokens = extractor(body)
        
        send_span(
            model=model_id,
            prompt_tokens=tokens["prompt_tokens"],
            completion_tokens=tokens["completion_tokens"],
            duration_ms=int((time.time() - start) * 1000)
        )
        
        return response
    
    client.invoke_model = tracked_invoke

if __name__ == "__main__":
    import boto3
    client = boto3.client("bedrock-runtime", region_name="us-east-1")
    install(client)
    
    # Test Claude on Bedrock
    response = client.invoke_model(
        modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 10,
            "messages": [{"role": "user", "content": "Say hi"}]
        })
    )
    print("Claude span sent:", json.loads(response["body"].read()))

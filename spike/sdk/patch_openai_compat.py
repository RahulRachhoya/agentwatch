"""
OpenAI-compatible API auto-instrumentation.

Reuses patch_openai logic but overrides provider field based on base_url.
Supports DeepSeek (https://api.deepseek.com), Kimi/Moonshot (https://api.moonshot.cn).
"""
import time
import os
import httpx

AGENTWATCH_URL = os.getenv("AGENTWATCH_URL", "http://localhost:8000")

def _detect_provider(base_url: str) -> str:
    """Map base_url to provider string."""
    if not base_url:
        return "openai"
    if "deepseek" in base_url:
        return "deepseek"
    if "moonshot" in base_url:
        return "moonshot"
    return "openai-compatible"

def send_span(provider: str, model: str, prompt_tokens: int, completion_tokens: int, duration_ms: int):
    try:
        httpx.post(
            f"{AGENTWATCH_URL}/v1/spans/batch",
            json={
                "spans": [{
                    "span_id": f"{provider}-{int(time.time() * 1000)}",
                    "run_id": f"spike-{provider}-test",
                    "name": f"{provider}.chat.completions.create",
                    "span_type": "llm",
                    "start_time": time.time() - (duration_ms / 1000),
                    "end_time": time.time(),
                    "provider": provider,
                    "model": model,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                    "metadata": {"source": f"{provider}_patch"}
                }]
            },
            timeout=5.0
        )
    except Exception:
        pass

def install(client):
    """Patch OpenAI-compatible client."""
    original_create = client.chat.completions.create
    provider = _detect_provider(getattr(client, "base_url", None))
    
    def tracked_create(*args, **kwargs):
        start = time.time()
        
        if kwargs.get('stream'):
            if 'stream_options' not in kwargs:
                kwargs['stream_options'] = {"include_usage": True}
        
        response = original_create(*args, **kwargs)
        
        if kwargs.get('stream'):
            chunks = []
            usage = None
            for chunk in response:
                chunks.append(chunk)
                if hasattr(chunk, 'usage') and chunk.usage:
                    usage = chunk.usage
            
            if usage:
                send_span(
                    provider=provider,
                    model=kwargs.get('model', 'unknown'),
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    duration_ms=int((time.time() - start) * 1000)
                )
            
            return (c for c in chunks)
        else:
            send_span(
                provider=provider,
                model=kwargs.get('model', 'unknown'),
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                duration_ms=int((time.time() - start) * 1000)
            )
            return response
    
    client.chat.completions.create = tracked_create

if __name__ == "__main__":
    from openai import OpenAI
    
    # Test DeepSeek
    deepseek = OpenAI(base_url="https://api.deepseek.com", api_key=os.getenv("DEEPSEEK_API_KEY"))
    install(deepseek)
    response = deepseek.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": "Say hi"}],
        max_tokens=10
    )
    print("DeepSeek span sent:", response.choices[0].message.content)
    
    # Test Kimi
    kimi = OpenAI(base_url="https://api.moonshot.cn/v1", api_key=os.getenv("MOONSHOT_API_KEY"))
    install(kimi)
    response = kimi.chat.completions.create(
        model="moonshot-v1-8k",
        messages=[{"role": "user", "content": "Say hi"}],
        max_tokens=10
    )
    print("Kimi span sent:", response.choices[0].message.content)

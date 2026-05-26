import time
import httpx
from anthropic import Anthropic
from datetime import datetime

BACKEND_URL = "http://localhost:8000"

def install(client: Anthropic):
    original_create = client.messages.create
    
    def tracked_create(*args, **kwargs):
        start = time.time()
        response = original_create(*args, **kwargs)
        
        send_span(
            model=kwargs.get('model', 'unknown'),
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            duration_ms=int((time.time() - start) * 1000)
        )
        return response
    
    client.messages.create = tracked_create

def send_span(model, prompt_tokens, completion_tokens, duration_ms):
    span = {
        "span_id": f"span_{int(time.time() * 1000)}",
        "run_id": "test_run",
        "span_type": "llm",
        "name": model,
        "model": model,
        "provider": "anthropic",
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "started_at": datetime.utcnow().isoformat(),
        "status": "success",
        "metadata": {"source": "native"}
    }
    try:
        httpx.post(f"{BACKEND_URL}/v1/spans/batch", json={"spans": [span]}, timeout=5)
    except:
        pass

if __name__ == "__main__":
    import os
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    install(client)
    
    response = client.messages.create(
        model="claude-3-5-haiku-20241022", 
        max_tokens=20, 
        messages=[{"role": "user", "content": "Hi"}]
    )
    print(f"Tokens: {response.usage.input_tokens + response.usage.output_tokens}")

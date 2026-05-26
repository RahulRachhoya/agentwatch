import time
import httpx
from openai import OpenAI
from datetime import datetime

BACKEND_URL = "http://localhost:8000"

def install(client: OpenAI):
    original_create = client.chat.completions.create
    
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
                    model=kwargs.get('model', 'unknown'),
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    duration_ms=int((time.time() - start) * 1000)
                )
            return chunks
        else:
            send_span(
                model=kwargs.get('model', 'unknown'),
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                duration_ms=int((time.time() - start) * 1000)
            )
            return response
    
    client.chat.completions.create = tracked_create

def send_span(model, prompt_tokens, completion_tokens, duration_ms):
    span = {
        "span_id": f"span_{int(time.time() * 1000)}",
        "run_id": "test_run",
        "span_type": "llm",
        "name": model,
        "model": model,
        "provider": "openai",
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
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    install(client)
    
    response = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": "Hi"}])
    print(f"Sync: {response.usage.total_tokens} tokens")
    
    stream = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": "Hi"}], stream=True)
    for chunk in stream:
        pass
    print("Stream: complete")

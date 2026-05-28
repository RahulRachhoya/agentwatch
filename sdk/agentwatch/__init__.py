import logging
from typing import Any, Optional

from agentwatch.client import AgentWatchClient
from agentwatch.patches.openai import patch_openai as _patch_openai, current_run_id
from agentwatch.patches.anthropic import patch_anthropic as _patch_anthropic
from agentwatch.patches.bedrock import patch_bedrock as _patch_bedrock
try:
    from agentwatch.langchain import AgentWatchCallbackHandler
except (ImportError, ModuleNotFoundError) as e:
    class AgentWatchCallbackHandler:  # type: ignore
        def __init__(self, *args, **kwargs):
            raise ImportError(
                "LangChain is not installed in this environment. Please run 'pip install langchain' to use the callback handler."
            )

logger = logging.getLogger("agentwatch")

# Global SDK client instance
_global_client: Optional[AgentWatchClient] = None

def init(url: str, api_key: Optional[str] = None) -> AgentWatchClient:
    """
    Initialize the AgentWatch SDK with the server URL and optional authorization key.
    
    Args:
        url: Backend server URL (e.g. 'http://localhost:8000')
        api_key: Optional X-API-Key value
    """
    global _global_client
    _global_client = AgentWatchClient(backend_url=url, api_key=api_key)
    logger.info(f"AgentWatch SDK initialized targeting backend: {url}")
    return _global_client

def get_client() -> AgentWatchClient:
    """Retrieve the global SDK client, raising an error if it hasn't been initialized."""
    global _global_client
    if not _global_client:
        raise ValueError(
            "AgentWatch SDK has not been initialized. Please call agentwatch.init('http://localhost:8000') first."
        )
    return _global_client

def patch_openai(client: Any, provider: Optional[str] = None):
    """
    Patch an OpenAI or AsyncOpenAI client instance to automatically track completions.
    
    Args:
        client: openai.OpenAI or openai.AsyncOpenAI client instance
        provider: Optional override to classify the provider (e.g. 'deepseek', 'moonshot')
    """
    _patch_openai(client, get_client(), provider=provider)

def patch_anthropic(client: Any):
    """
    Patch an Anthropic or AsyncAnthropic client instance to automatically track message generations.
    """
    _patch_anthropic(client, get_client())

def patch_bedrock(client: Any):
    """
    Patch a boto3 bedrock-runtime client instance to automatically track model inferences.
    """
    _patch_bedrock(client, get_client())

__all__ = [
    "init",
    "get_client",
    "patch_openai",
    "patch_anthropic",
    "patch_bedrock",
    "AgentWatchCallbackHandler",
    "current_run_id"
]

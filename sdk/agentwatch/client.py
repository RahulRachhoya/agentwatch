import logging
import httpx
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

logger = logging.getLogger("agentwatch")

class AgentWatchClient:
    """Core SDK client for posting runs and spans to AgentWatch backend asynchronously."""
    
    def __init__(self, backend_url: str, api_key: Optional[str] = None):
        self.backend_url = backend_url.rstrip("/")
        self.api_key = api_key
        # Thread pool to dispatch exports in background without blocking application execution
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["X-API-Key"] = api_key

    def _post(self, path: str, json_data: Any):
        url = f"{self.backend_url}{path}"
        try:
            with httpx.Client(headers=self.headers, timeout=5.0) as client:
                res = client.post(url, json=json_data)
                res.raise_for_status()
        except Exception as e:
            logger.warning(f"AgentWatch client failed to post to {url}: {e}")

    def _patch(self, path: str, json_data: Any):
        url = f"{self.backend_url}{path}"
        try:
            with httpx.Client(headers=self.headers, timeout=5.0) as client:
                res = client.patch(url, json=json_data)
                res.raise_for_status()
        except Exception as e:
            logger.warning(f"AgentWatch client failed to patch to {url}: {e}")

    def create_run(
        self, 
        run_id: str, 
        name: str, 
        session_id: Optional[str] = None, 
        tags: List[str] = [], 
        metadata: Dict[str, Any] = {}
    ):
        """Asynchronously create a run."""
        payload = {
            "run_id": run_id,
            "name": name,
            "session_id": session_id,
            "tags": tags,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata
        }
        self.executor.submit(self._post, "/v1/runs", payload)

    def update_run(self, run_id: str, status: str, error_message: Optional[str] = None):
        """Asynchronously complete or fail a run."""
        payload = {
            "status": status,
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "error_message": error_message
        }
        self.executor.submit(self._patch, f"/v1/runs/{run_id}", payload)

    def send_spans(self, spans: List[Dict[str, Any]]):
        """Asynchronously send a batch of spans."""
        payload = {"spans": spans}
        self.executor.submit(self._post, "/v1/spans/batch", payload)

import asyncio
import json
import uuid
from typing import Any

import httpx
import websockets

from src.core.config import get_settings
from src.services.runpod.pod_manager import runpod_manager

settings = get_settings()


class ComfyUIClient:
    """WebSocket client for ComfyUI API with RunPod integration."""

    def __init__(self):
        self.client_id = str(uuid.uuid4())
        self._http_url: str | None = None
        self._ws_url: str | None = None

    async def _get_http_url(self) -> str:
        """Get HTTP URL, using RunPod if configured."""
        if self._http_url is None:
            self._http_url = await runpod_manager.get_comfyui_url()
        return self._http_url

    async def _get_ws_url(self) -> str:
        """Get WebSocket URL, using RunPod if configured."""
        if self._ws_url is None:
            self._ws_url = await runpod_manager.get_comfyui_ws_url()
        return self._ws_url

    def reset_urls(self) -> None:
        """Reset cached URLs to force refresh on next request."""
        self._http_url = None
        self._ws_url = None

    async def health_check(self) -> bool:
        """Check if ComfyUI is reachable and healthy."""
        try:
            http_url = await self._get_http_url()
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{http_url}/system_stats",
                    timeout=10.0,
                )
                return response.status_code == 200
        except Exception:
            return False

    async def queue_prompt(self, workflow: dict[str, Any]) -> str:
        """Queue a workflow and return the prompt_id."""
        http_url = await self._get_http_url()
        payload = {
            "prompt": workflow,
            "client_id": self.client_id,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{http_url}/prompt",
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["prompt_id"]

    async def get_history(self, prompt_id: str) -> dict[str, Any]:
        """Get the history/output for a prompt."""
        http_url = await self._get_http_url()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{http_url}/history/{prompt_id}",
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def get_image(
        self, filename: str, subfolder: str = "", folder_type: str = "output"
    ) -> bytes:
        """Download an image from ComfyUI."""
        http_url = await self._get_http_url()
        params = {
            "filename": filename,
            "subfolder": subfolder,
            "type": folder_type,
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{http_url}/view",
                params=params,
                timeout=60.0,
            )
            response.raise_for_status()
            return response.content

    async def upload_image(self, image_data: bytes, filename: str) -> dict[str, Any]:
        """Upload an image to ComfyUI input folder."""
        http_url = await self._get_http_url()
        async with httpx.AsyncClient() as client:
            files = {"image": (filename, image_data, "image/png")}
            response = await client.post(
                f"{http_url}/upload/image",
                files=files,
                timeout=60.0,
            )
            response.raise_for_status()
            return response.json()

    async def execute_workflow(
        self,
        workflow: dict[str, Any],
        timeout: float = 300.0,
    ) -> dict[str, Any]:
        """
        Execute a workflow and wait for completion.

        Returns the output images/videos from the workflow.
        """
        ws_url = await self._get_ws_url()
        prompt_id = await self.queue_prompt(workflow)

        async with websockets.connect(f"{ws_url}?clientId={self.client_id}") as ws:
            start_time = asyncio.get_event_loop().time()

            while True:
                if asyncio.get_event_loop().time() - start_time > timeout:
                    raise TimeoutError(f"Workflow execution timed out after {timeout}s")

                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    data = json.loads(message)

                    if data.get("type") == "executing":
                        exec_data = data.get("data", {})
                        if exec_data.get("prompt_id") == prompt_id:
                            if exec_data.get("node") is None:
                                # Execution complete
                                break

                    elif data.get("type") == "execution_error":
                        error_data = data.get("data", {})
                        if error_data.get("prompt_id") == prompt_id:
                            raise RuntimeError(
                                f"Workflow execution failed: {error_data.get('exception_message', 'Unknown error')}"
                            )

                except asyncio.TimeoutError:
                    continue

        # Get the output
        history = await self.get_history(prompt_id)
        return history.get(prompt_id, {}).get("outputs", {})


# Global client instance
comfyui_client = ComfyUIClient()

"""
RunPod Pod Manager

Manages GPU pods on RunPod for ComfyUI workloads.
Provides pod selection, health checking, and scaling support.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

import httpx

from src.core.config import get_settings

settings = get_settings()


class PodStatus(str, Enum):
    RUNNING = "RUNNING"
    STARTING = "STARTING"
    STOPPED = "STOPPED"
    EXITED = "EXITED"
    ERROR = "ERROR"


@dataclass
class Pod:
    id: str
    name: str
    status: PodStatus
    gpu_type: str
    comfyui_url: str | None
    last_health_check: datetime | None = None
    is_healthy: bool = False


class RunPodManager:
    """
    Manages RunPod GPU pods for distributed ComfyUI workloads.

    Supports:
    - Multi-pod load balancing
    - Health checking
    - Dynamic pod selection
    - Failover to healthy pods
    """

    BASE_URL = "https://api.runpod.io/graphql"

    def __init__(self):
        self.api_key = settings.runpod_api_key
        self.endpoint_id = settings.runpod_endpoint_id
        self._pods: dict[str, Pod] = {}
        self._health_check_interval = 30  # seconds
        self._last_refresh: datetime | None = None

    @property
    def is_configured(self) -> bool:
        """Check if RunPod is properly configured."""
        return bool(self.api_key and self.endpoint_id)

    async def _graphql_request(self, query: str, variables: dict | None = None) -> dict:
        """Make a GraphQL request to RunPod API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.BASE_URL,
                headers=headers,
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            if "errors" in data:
                raise RuntimeError(f"RunPod API error: {data['errors']}")

            return data.get("data", {})

    async def list_pods(self) -> list[Pod]:
        """List all pods from RunPod account."""
        if not self.is_configured:
            return []

        query = """
        query {
            myself {
                pods {
                    id
                    name
                    desiredStatus
                    runtime {
                        ports {
                            ip
                            isIpPublic
                            privatePort
                            publicPort
                        }
                    }
                    machine {
                        gpuDisplayName
                    }
                }
            }
        }
        """

        data = await self._graphql_request(query)
        pods_data = data.get("myself", {}).get("pods", [])

        pods = []
        for pod_data in pods_data:
            # Find ComfyUI port (usually 8188)
            comfyui_url = None
            runtime = pod_data.get("runtime")
            if runtime and runtime.get("ports"):
                for port in runtime["ports"]:
                    if port.get("privatePort") == 8188 and port.get("isIpPublic"):
                        ip = port.get("ip")
                        public_port = port.get("publicPort")
                        if ip and public_port:
                            comfyui_url = f"http://{ip}:{public_port}"
                            break

            status_str = pod_data.get("desiredStatus", "STOPPED")
            try:
                status = PodStatus(status_str)
            except ValueError:
                status = PodStatus.ERROR

            pod = Pod(
                id=pod_data["id"],
                name=pod_data.get("name", ""),
                status=status,
                gpu_type=pod_data.get("machine", {}).get("gpuDisplayName", "Unknown"),
                comfyui_url=comfyui_url,
            )
            pods.append(pod)

        return pods

    async def check_pod_health(self, pod: Pod) -> bool:
        """Check if a pod's ComfyUI instance is healthy."""
        if not pod.comfyui_url:
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{pod.comfyui_url}/system_stats",
                    timeout=10.0,
                )
                is_healthy = response.status_code == 200
                pod.is_healthy = is_healthy
                pod.last_health_check = datetime.utcnow()
                return is_healthy
        except Exception:
            pod.is_healthy = False
            pod.last_health_check = datetime.utcnow()
            return False

    async def refresh_pods(self, force: bool = False) -> None:
        """Refresh pod list and health status."""
        now = datetime.utcnow()

        # Skip if recently refreshed
        if not force and self._last_refresh:
            if now - self._last_refresh < timedelta(seconds=self._health_check_interval):
                return

        pods = await self.list_pods()

        # Check health in parallel
        health_tasks = [self.check_pod_health(pod) for pod in pods]
        await asyncio.gather(*health_tasks, return_exceptions=True)

        # Update cache
        self._pods = {pod.id: pod for pod in pods}
        self._last_refresh = now

    async def get_available_pod(self) -> Pod | None:
        """
        Get a healthy, available pod for workload execution.

        Uses simple round-robin with health check fallback.
        """
        await self.refresh_pods()

        # Filter to healthy, running pods
        healthy_pods = [
            pod for pod in self._pods.values()
            if pod.status == PodStatus.RUNNING and pod.is_healthy and pod.comfyui_url
        ]

        if not healthy_pods:
            return None

        # Simple selection - could be enhanced with load balancing
        return healthy_pods[0]

    async def get_comfyui_url(self) -> str:
        """
        Get ComfyUI URL for the best available pod.

        Falls back to configured default if RunPod not available.
        """
        if not self.is_configured:
            # Fall back to static configuration
            return settings.comfyui_http_url

        pod = await self.get_available_pod()
        if pod and pod.comfyui_url:
            return pod.comfyui_url

        # Fall back to static configuration
        return settings.comfyui_http_url

    async def get_comfyui_ws_url(self) -> str:
        """Get WebSocket URL for ComfyUI."""
        http_url = await self.get_comfyui_url()
        # Convert http:// to ws://
        ws_url = http_url.replace("http://", "ws://").replace("https://", "wss://")
        return f"{ws_url}/ws"

    async def start_pod(self, pod_id: str) -> bool:
        """Start a stopped pod."""
        if not self.is_configured:
            return False

        mutation = """
        mutation($podId: String!) {
            podResume(input: { podId: $podId }) {
                id
                desiredStatus
            }
        }
        """

        try:
            await self._graphql_request(mutation, {"podId": pod_id})
            return True
        except Exception:
            return False

    async def stop_pod(self, pod_id: str) -> bool:
        """Stop a running pod."""
        if not self.is_configured:
            return False

        mutation = """
        mutation($podId: String!) {
            podStop(input: { podId: $podId }) {
                id
                desiredStatus
            }
        }
        """

        try:
            await self._graphql_request(mutation, {"podId": pod_id})
            return True
        except Exception:
            return False


# Global instance
runpod_manager = RunPodManager()

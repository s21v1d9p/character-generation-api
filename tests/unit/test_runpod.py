import pytest
from unittest.mock import AsyncMock, patch


class TestRunPodManager:
    @pytest.fixture
    def runpod_manager(self):
        """Create RunPod manager for testing."""
        with patch("src.services.runpod.pod_manager.get_settings") as mock_settings:
            mock_settings.return_value.runpod_api_key = "test_key"
            mock_settings.return_value.runpod_endpoint_id = "test_endpoint"
            mock_settings.return_value.comfyui_http_url = "http://localhost:8188"
            mock_settings.return_value.comfyui_url = "ws://localhost:8188/ws"

            from src.services.runpod.pod_manager import RunPodManager
            return RunPodManager()

    def test_is_configured_with_credentials(self, runpod_manager):
        """Test that manager detects when configured."""
        assert runpod_manager.is_configured is True

    def test_is_configured_without_credentials(self):
        """Test that manager detects when not configured."""
        with patch("src.services.runpod.pod_manager.get_settings") as mock_settings:
            mock_settings.return_value.runpod_api_key = ""
            mock_settings.return_value.runpod_endpoint_id = ""

            from src.services.runpod.pod_manager import RunPodManager
            manager = RunPodManager()
            assert manager.is_configured is False

    @pytest.mark.anyio
    async def test_get_comfyui_url_fallback(self):
        """Test fallback to static URL when RunPod not configured."""
        with patch("src.services.runpod.pod_manager.get_settings") as mock_settings:
            mock_settings.return_value.runpod_api_key = ""
            mock_settings.return_value.runpod_endpoint_id = ""
            mock_settings.return_value.comfyui_http_url = "http://localhost:8188"

            from src.services.runpod.pod_manager import RunPodManager
            manager = RunPodManager()
            url = await manager.get_comfyui_url()
            assert url == "http://localhost:8188"


class TestComfyUIClient:
    @pytest.mark.anyio
    async def test_health_check_returns_bool(self):
        """Test that health check returns boolean."""
        with patch("src.services.comfyui.client.runpod_manager") as mock_runpod:
            mock_runpod.get_comfyui_url = AsyncMock(return_value="http://localhost:8188")

            with patch("src.services.comfyui.client.httpx.AsyncClient") as mock_client:
                mock_response = AsyncMock()
                mock_response.status_code = 200
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                    return_value=mock_response
                )

                from src.services.comfyui.client import ComfyUIClient
                client = ComfyUIClient()
                result = await client.health_check()
                assert isinstance(result, bool)

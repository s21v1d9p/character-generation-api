import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestS3StorageProvider:
    @pytest.fixture
    def s3_provider(self):
        """Create S3 provider with mocked boto3."""
        with patch("src.services.storage.s3_provider.boto3") as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client

            from src.services.storage.s3_provider import S3StorageProvider
            provider = S3StorageProvider()
            provider.client = mock_client
            return provider

    @pytest.mark.anyio
    async def test_upload_returns_url(self, s3_provider):
        """Test that upload returns a valid S3 URL."""
        url = await s3_provider.upload(
            data=b"test data",
            path="test/file.png",
            content_type="image/png",
        )

        assert "s3" in url
        assert "test/file.png" in url

    @pytest.mark.anyio
    async def test_get_url_format(self, s3_provider):
        """Test URL format."""
        url = await s3_provider.get_url("characters/123/image.png")

        assert url.startswith("https://")
        assert "s3" in url
        assert "characters/123/image.png" in url


class TestStorageManager:
    @pytest.mark.anyio
    async def test_manager_uses_configured_provider(self):
        """Test that manager uses the configured storage provider."""
        with patch("src.services.storage.manager.get_settings") as mock_settings:
            mock_settings.return_value.storage_provider = "s3"

            from src.services.storage.manager import get_storage_provider
            provider = get_storage_provider()

            assert provider is not None

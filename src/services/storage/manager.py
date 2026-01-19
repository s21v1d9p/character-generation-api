from src.core.config import get_settings
from src.services.storage.base import BaseStorageProvider

settings = get_settings()


def get_storage_provider() -> BaseStorageProvider:
    """Factory function to get the configured storage provider."""
    if settings.storage_provider == "s3":
        from src.services.storage.s3_provider import S3StorageProvider
        return S3StorageProvider()
    elif settings.storage_provider == "supabase":
        from src.services.storage.supabase_provider import SupabaseStorageProvider
        return SupabaseStorageProvider()
    elif settings.storage_provider == "local":
        from src.services.storage.local_provider import LocalStorageProvider
        return LocalStorageProvider()
    else:
        raise ValueError(f"Unknown storage provider: {settings.storage_provider}")


class StorageManager:
    """
    Storage manager with lazy initialization.

    Provides a unified interface to upload/download regardless of provider.
    """

    _provider: BaseStorageProvider | None = None

    @property
    def provider(self) -> BaseStorageProvider:
        if self._provider is None:
            self._provider = get_storage_provider()
        return self._provider

    async def upload(
        self,
        data: bytes,
        path: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload data and return the public URL."""
        return await self.provider.upload(data, path, content_type)

    async def delete(self, path: str) -> None:
        """Delete a file from storage."""
        await self.provider.delete(path)

    async def get_url(self, path: str) -> str:
        """Get the public URL for a file."""
        return await self.provider.get_url(path)


# Global storage manager instance
storage_manager = StorageManager()

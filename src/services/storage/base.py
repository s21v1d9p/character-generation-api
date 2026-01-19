from abc import ABC, abstractmethod


class BaseStorageProvider(ABC):
    """Abstract base class for storage providers."""

    @abstractmethod
    async def upload(
        self,
        data: bytes,
        path: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Upload data to storage and return the public URL.

        Args:
            data: File content as bytes
            path: Storage path (e.g., "characters/123/images/456.png")
            content_type: MIME type of the file

        Returns:
            Public URL to access the uploaded file
        """
        pass

    @abstractmethod
    async def delete(self, path: str) -> None:
        """Delete a file from storage."""
        pass

    @abstractmethod
    async def get_url(self, path: str) -> str:
        """Get the public URL for a stored file."""
        pass

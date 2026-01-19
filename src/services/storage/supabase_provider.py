from supabase import create_client

from src.core.config import get_settings
from src.services.storage.base import BaseStorageProvider

settings = get_settings()


class SupabaseStorageProvider(BaseStorageProvider):
    """Supabase storage provider."""

    def __init__(self):
        self.bucket = settings.supabase_bucket
        self.client = create_client(
            settings.supabase_url,
            settings.supabase_key,
        )

    async def upload(
        self,
        data: bytes,
        path: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload data to Supabase Storage and return the public URL."""
        self.client.storage.from_(self.bucket).upload(
            path,
            data,
            file_options={"content-type": content_type},
        )

        return await self.get_url(path)

    async def get_url(self, path: str) -> str:
        """Get the public URL for a Supabase Storage object."""
        response = self.client.storage.from_(self.bucket).get_public_url(path)
        return response

    async def delete(self, path: str) -> None:
        """Delete an object from Supabase Storage."""
        self.client.storage.from_(self.bucket).remove([path])

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial

import boto3
from botocore.config import Config

from src.core.config import get_settings
from src.services.storage.base import BaseStorageProvider

settings = get_settings()

# Thread pool for running sync boto3 calls
_executor = ThreadPoolExecutor(max_workers=4)


class S3StorageProvider(BaseStorageProvider):
    """AWS S3 storage provider with async support."""

    def __init__(self):
        self.bucket = settings.s3_bucket
        self.region = settings.aws_region

        self.client = boto3.client(
            "s3",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=self.region,
            config=Config(signature_version="s3v4"),
        )

    async def _run_sync(self, func, *args, **kwargs):
        """Run a synchronous function in a thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor, partial(func, *args, **kwargs)
        )

    async def upload(
        self,
        data: bytes,
        path: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload data to S3 and return the public URL."""
        await self._run_sync(
            self.client.put_object,
            Bucket=self.bucket,
            Key=path,
            Body=data,
            ContentType=content_type,
        )

        return self.get_url_sync(path)

    def get_url_sync(self, path: str) -> str:
        """Get the public URL for an S3 object."""
        return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{path}"

    async def get_url(self, path: str) -> str:
        """Get the public URL for an S3 object."""
        return self.get_url_sync(path)

    async def delete(self, path: str) -> None:
        """Delete an object from S3."""
        await self._run_sync(
            self.client.delete_object,
            Bucket=self.bucket,
            Key=path,
        )

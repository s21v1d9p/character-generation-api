from pathlib import Path

from .base import BaseStorageProvider


class LocalStorageProvider(BaseStorageProvider):
    """Local filesystem storage provider for development/testing."""

    def __init__(self, base_dir: str = "/workspace/storage"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def upload(
        self,
        data: bytes,
        path: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        dest_path = self.base_dir / path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(data)
        return f"file://{dest_path}"

    async def delete(self, path: str) -> None:
        file_path = self.base_dir / path
        if file_path.exists():
            file_path.unlink()

    async def get_url(self, path: str) -> str:
        return f"file://{self.base_dir / path}"

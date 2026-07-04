"""File storage service supporting local and S3 backends."""

import hashlib
import os
import shutil
import uuid
from pathlib import Path
from typing import Optional

import aiofiles

from app.core.config import settings


class StorageService:
    def __init__(self):
        self.backend = settings.STORAGE_BACKEND
        if self.backend == "local":
            self.base_path = settings.storage_path
            (self.base_path / "documents").mkdir(parents=True, exist_ok=True)
            (self.base_path / "pages").mkdir(parents=True, exist_ok=True)
            (self.base_path / "exports").mkdir(parents=True, exist_ok=True)
            (self.base_path / "temp").mkdir(parents=True, exist_ok=True)

    async def save_file(
        self, content: bytes, filename: str, subfolder: str = "documents"
    ) -> tuple[str, str, int]:
        """Save file and return (path, hash, size)."""
        file_hash = hashlib.sha256(content).hexdigest()
        file_size = len(content)
        ext = Path(filename).suffix
        stored_name = f"{uuid.uuid4().hex}{ext}"

        if self.backend == "local":
            file_path = self.base_path / subfolder / stored_name
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(content)
            return str(file_path), file_hash, file_size
        elif self.backend == "s3":
            return await self._save_to_s3(content, stored_name, subfolder)

    async def _save_to_s3(
        self, content: bytes, stored_name: str, subfolder: str
    ) -> tuple[str, str, int]:
        import boto3

        s3 = boto3.client(
            "s3",
            region_name=settings.S3_REGION,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            endpoint_url=settings.S3_ENDPOINT_URL or None,
        )
        key = f"{subfolder}/{stored_name}"
        s3.put_object(Bucket=settings.S3_BUCKET, Key=key, Body=content)
        file_hash = hashlib.sha256(content).hexdigest()
        return f"s3://{settings.S3_BUCKET}/{key}", file_hash, len(content)

    async def read_file(self, file_path: str) -> bytes:
        if file_path.startswith("s3://"):
            return await self._read_from_s3(file_path)
        async with aiofiles.open(file_path, "rb") as f:
            return await f.read()

    async def _read_from_s3(self, file_path: str) -> bytes:
        import boto3

        s3 = boto3.client(
            "s3",
            region_name=settings.S3_REGION,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            endpoint_url=settings.S3_ENDPOINT_URL or None,
        )
        parts = file_path.replace("s3://", "").split("/", 1)
        bucket, key = parts[0], parts[1]
        response = s3.get_object(Bucket=bucket, Key=key)
        return response["Body"].read()

    async def delete_file(self, file_path: str) -> None:
        if file_path.startswith("s3://"):
            await self._delete_from_s3(file_path)
        else:
            path = Path(file_path)
            if path.exists():
                path.unlink()

    async def _delete_from_s3(self, file_path: str) -> None:
        import boto3

        s3 = boto3.client(
            "s3",
            region_name=settings.S3_REGION,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            endpoint_url=settings.S3_ENDPOINT_URL or None,
        )
        parts = file_path.replace("s3://", "").split("/", 1)
        s3.delete_object(Bucket=parts[0], Key=parts[1])

    async def get_storage_usage(self) -> int:
        """Return total storage used in bytes."""
        if self.backend == "local":
            total = 0
            for dirpath, _, filenames in os.walk(self.base_path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    total += os.path.getsize(fp)
            return total
        return 0

    async def save_temp_file(self, content: bytes, filename: str) -> str:
        """Save a temporary file for processing."""
        path, _, _ = await self.save_file(content, filename, "temp")
        return path

    async def cleanup_temp(self) -> None:
        """Remove all temp files."""
        if self.backend == "local":
            temp_dir = self.base_path / "temp"
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
                temp_dir.mkdir(parents=True, exist_ok=True)


storage_service = StorageService()

"""S3 / MinIO storage service for meeting audio and artifacts."""

import hashlib
import uuid
from datetime import datetime
from typing import BinaryIO

import aioboto3
from botocore.config import Config

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class StorageService:
    def __init__(self) -> None:
        self.session = aioboto3.Session()
        self.bucket = settings.s3_bucket
        self.endpoint = settings.s3_endpoint
        self.region = settings.s3_region

    def _client_kwargs(self) -> dict:
        return {
            "service_name": "s3",
            "endpoint_url": self.endpoint,
            "aws_access_key_id": settings.s3_access_key,
            "aws_secret_access_key": settings.s3_secret_key,
            "region_name": self.region,
            "config": Config(signature_version="s3v4"),
        }

    @staticmethod
    def build_key(
        organization_id: uuid.UUID,
        meeting_id: uuid.UUID,
        filename: str,
        prefix: str = "recordings",
    ) -> str:
        ts = datetime.utcnow().strftime("%Y%m%d")
        safe_name = filename.replace(" ", "_")[:200]
        return f"{prefix}/{organization_id}/{ts}/{meeting_id}/{safe_name}"

    async def ensure_bucket(self) -> None:
        async with self.session.client(**self._client_kwargs()) as client:
            try:
                await client.head_bucket(Bucket=self.bucket)
            except Exception:
                logger.info("creating_bucket", bucket=self.bucket)
                await client.create_bucket(Bucket=self.bucket)

    async def upload_file(
        self,
        file_obj: BinaryIO | bytes,
        key: str,
        content_type: str = "application/octet-stream",
        metadata: dict | None = None,
    ) -> dict:
        if isinstance(file_obj, bytes):
            body = file_obj
            size = len(body)
            checksum = hashlib.sha256(body).hexdigest()
        else:
            body = file_obj.read()
            size = len(body)
            checksum = hashlib.sha256(body).hexdigest()
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)

        extra_args: dict = {"ContentType": content_type}
        if metadata:
            extra_args["Metadata"] = {k: str(v) for k, v in metadata.items()}

        async with self.session.client(**self._client_kwargs()) as client:
            await client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=body,
                **extra_args,
            )

        logger.info("file_uploaded", key=key, size=size, content_type=content_type)
        return {
            "bucket": self.bucket,
            "key": key,
            "size": size,
            "checksum": checksum,
            "content_type": content_type,
        }

    async def download_bytes(self, key: str) -> bytes:
        async with self.session.client(**self._client_kwargs()) as client:
            resp = await client.get_object(Bucket=self.bucket, Key=key)
            async with resp["Body"] as stream:
                return await stream.read()

    async def generate_presigned_url(
        self, key: str, expires_in: int = 3600, method: str = "get_object"
    ) -> str:
        async with self.session.client(**self._client_kwargs()) as client:
            return await client.generate_presigned_url(
                ClientMethod=method,
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in,
            )

    async def delete_object(self, key: str) -> None:
        async with self.session.client(**self._client_kwargs()) as client:
            await client.delete_object(Bucket=self.bucket, Key=key)
            logger.info("file_deleted", key=key)


def get_storage_service() -> StorageService:
    return StorageService()

"""
Object storage abstraction — wraps boto3 for S3-compatible backends
(AWS S3, Cloudflare R2, MinIO).
"""

import uuid
import aioboto3
from .config import get_settings

settings = get_settings()


class StorageService:
    def __init__(self) -> None:
        self._session = aioboto3.Session(
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
            region_name=settings.storage_region,
        )
        self._bucket = settings.storage_bucket
        self._endpoint_url = settings.storage_endpoint_url

    def _client(self):
        kwargs = {"service_name": "s3"}
        if self._endpoint_url:
            kwargs["endpoint_url"] = self._endpoint_url
        return self._session.client(**kwargs)

    async def upload_file(self, file_bytes: bytes, content_type: str = "application/pdf") -> str:
        """Upload bytes to storage and return the storage key."""
        key = f"uploads/{uuid.uuid4()}.pdf"
        async with self._client() as s3:
            await s3.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=file_bytes,
                ContentType=content_type,
            )
        return key

    async def download_file(self, storage_key: str) -> bytes:
        async with self._client() as s3:
            response = await s3.get_object(Bucket=self._bucket, Key=storage_key)
            return await response["Body"].read()

    async def delete_file(self, storage_key: str) -> None:
        async with self._client() as s3:
            await s3.delete_object(Bucket=self._bucket, Key=storage_key)

    async def get_presigned_url(self, storage_key: str, expires_in: int = 3600) -> str:
        async with self._client() as s3:
            return await s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": storage_key},
                ExpiresIn=expires_in,
            )

import asyncio
import boto3
from app.config import settings

class S3StorageService:
    def __init__(self) -> None:
        self.bucket = settings.aws_s3_bucket_name

        self.client = boto3.client(
            "s3",
            region_name=settings.aws_region,
        )

    async def upload(
        self,
        *,
        key: str,
        content: bytes,
        content_type: str,
    ) -> None:
        await asyncio.to_thread(
            self.client.put_object,
            Bucket=self.bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
        )

    async def download(
        self,
        *,
        key: str,
    ) -> bytes:
        response = await asyncio.to_thread(
            self.client.get_object,
            Bucket=self.bucket,
            Key=key,
        )

        return await asyncio.to_thread(
            response["Body"].read
        )

    async def delete(
        self,
        *,
        key: str,
    ) -> None:
        await asyncio.to_thread(
            self.client.delete_object,
            Bucket=self.bucket,
            Key=key,
        )
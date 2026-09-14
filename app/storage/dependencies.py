from functools import lru_cache

from app.storage.base import StorageService
from app.storage.s3 import S3StorageService


@lru_cache
def get_storage() -> StorageService:
    return S3StorageService()
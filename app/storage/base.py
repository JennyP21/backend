from typing import Protocol

class StorageService(Protocol):
    async def upload(
        self,
        *,
        key: str,
        content: bytes,
        content_type: str,
    ) -> None:
        ...

    async def download(
        self,
        *,
        key: str,
    ) -> bytes:
        ...

    async def delete(
        self,
        *,
        key: str,
    ) -> None:
        ...
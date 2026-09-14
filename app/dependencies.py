from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_user
from app.db.session import get_db
from app.storage.base import StorageService
from app.storage.dependencies import get_storage

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUserId = Annotated[str, Depends(require_user)]
Storage = Annotated[
    StorageService,
    Depends(get_storage),
]
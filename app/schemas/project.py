from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

class ProjectCreate(BaseModel):
    name: str = Field(
        min_length=3,
        max_length=100,
    )

    description: str | None = Field(
        default=None,
        max_length=2000,
    )


class ProjectUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=3,
        max_length=100,
    )

    description: str | None = Field(
        default=None,
        max_length=2000,
    )


class ProjectResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    name: str
    description: str | None

    created_at: datetime
    updated_at: datetime
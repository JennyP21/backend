from datetime import datetime
from uuid import UUID
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from app.models.document import DocumentStatus

class DocumentResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )
    
    id: UUID
    project_id: UUID
    
    original_filename: str
    
    mime_type: str
    
    file_size: int
    status: DocumentStatus
    
    page_count: int | None = None
    
    metadata: dict[str, Any] = Field(
        validation_alias="metadata_",
        default_factory=dict,
    )
    
    created_at: datetime
    updated_at: datetime
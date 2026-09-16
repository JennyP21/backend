from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.ingestion_batch import IngestionBatchStatus


class IngestionBatchResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    project_id: UUID
    status: IngestionBatchStatus
    queued_documents: int
    created_at: datetime
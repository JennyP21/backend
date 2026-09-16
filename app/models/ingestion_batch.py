import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IngestionBatchStatus(str, PyEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIALLY_FAILED = "partially_failed"
    FAILED = "failed"

class IngestionBatch(Base):
    __tablename__ = "ingestion_batches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id"),
        nullable=False,
    )

    created_by: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    status: Mapped[IngestionBatchStatus] = mapped_column(
        SQLEnum(
            IngestionBatchStatus,
            name="ingestion_batch_status",
            values_callable=lambda enum: [
                member.value for member in enum
            ],
        ),
        nullable=False,
        default=IngestionBatchStatus.QUEUED,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
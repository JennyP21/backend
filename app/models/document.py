import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import UUID, BigInteger, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class DocumentStatus(str, PyEnum):
    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"

class Document(Base):
    __tablename__ = "documents"
    
    __table_args__ = (
        Index(
            "ix_documents_project_created_at",
            "uploaded_by",
            "project_id",
        ),
    )
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id"),
        nullable=False
    )
    
    uploaded_by: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    
    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False
    )
    
    storage_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    
    status: Mapped[DocumentStatus] = mapped_column(
        SQLEnum(
            DocumentStatus,
            name="document_status",
            values_callable=lambda enum: [
                member.value for member in enum
            ],
        ),
        nullable=False,
        default=DocumentStatus.UPLOADED,
    )
    
    page_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )
    
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    
    
import uuid
from datetime import datetime, timezone
from uuid import UUID

from fastapi import (APIRouter, HTTPException, Query, Response, UploadFile,
                     status)
from sqlalchemy import select

from app.dependencies import CurrentUserId, DbSession, Storage
from app.models.document import Document
from app.schemas.document import DocumentDownloadResponse, DocumentResponse
from app.services.document import get_owned_document
from app.services.project import get_owned_project

router = APIRouter(
    tags=["Documents"],
)

MAX_FILE_SIZE = 30 * 1024 * 1024

@router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
)
async def get_document(
    document_id: UUID,
    user_id: CurrentUserId,
    db: DbSession
):
    return await get_owned_document(
        db=db,
        user_id=user_id,
        document_id=document_id
    )

@router.get(
    "/documents/{document_id}/download",
    response_model=DocumentDownloadResponse,
)
async def download_document(
    document_id: UUID,
    user_id: CurrentUserId,
    db: DbSession,
    storage: Storage,
):
    document = await get_owned_document(
        db=db,
        user_id=user_id,
        document_id=document_id,
    )

    expires_in = 300

    url = await storage.generate_download_url(
        key=document.storage_key,
        expires_in=expires_in,
    )

    return DocumentDownloadResponse(
        url=url,
        expires_in=expires_in,
    )

@router.get(
    "/projects/{project_id}/documents",
    response_model=list[DocumentResponse],
)
async def list_documents(
    project_id: UUID,
    user_id: CurrentUserId,
    db: DbSession,
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
):
    await get_owned_project(
        db=db,
        user_id=user_id,
        project_id=project_id,
    )

    result = await db.execute(
        select(Document)
        .where(
            Document.project_id == project_id,
            Document.deleted_at.is_(None),
        )
        .order_by(
            Document.created_at.desc()
        )
        .limit(limit)
        .offset(offset)
    )

    return result.scalars().all()

@router.post(
    "/projects/{project_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED
)
async def upload_document(
    project_id: UUID,
    file: UploadFile,
    user_id: CurrentUserId,
    db: DbSession,
    storage: Storage
):
    # 1. Verify project ownership
    await get_owned_project(
        db=db,
        user_id=user_id,
        project_id=project_id
    )
    
    # 2. Validate filename and Size
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required",
        )   

    # 3. Validate MIME type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=415,
            detail="Only PDF files are supported",
        )
        
    # 4. Read/validate size
    content = await file.read()
    file_size = len(content)
    if file_size == 0:
        raise HTTPException(
            status_code=400,
            detail="File cannot be empty",
        )
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds the 30 MB limit",
        )

    # 5. Generate document UUID
    document_uuid = uuid.uuid4()

    # 6. Generate storage key
    
    storage_key = (
        f"projects/{project_id}/"
        f"documents/{document_uuid}/source.pdf"
    )

    # 7. Upload to storage
    uploaded = False
    
    try:
        await storage.upload(
            key=storage_key,
            content=content,
            content_type=file.content_type
        )
        
        uploaded = True

        # 8. Create Document(
            
        document = Document(
            id=document_uuid,
            project_id=project_id,
            uploaded_by=user_id,
            original_filename=file.filename,
            mime_type=file.content_type,
            file_size=file_size,
            storage_key=storage_key,
            page_count=None,
            metadata_={},
        )

        db.add(document)
        
        await db.commit()
        await db.refresh(document)
        
        return document

    except Exception:
        await db.rollback()
        
        if uploaded:
            try:
                await storage.delete(
                    key=storage_key,
                )
            except Exception:
                pass
        
        raise
    
    finally:
        await file.close()
    
@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_document(
    document_id: UUID,
    user_id: CurrentUserId,
    db: DbSession,
    storage: Storage,
):
    document = await get_owned_document(
        db=db,
        user_id=user_id,
        document_id=document_id,
    )

    storage_key = document.storage_key

    document.deleted_at = datetime.now(timezone.utc)

    await db.commit()

    try:
        await storage.delete(
            key=storage_key,
        )
    except Exception:
        # Later: log this and enqueue storage cleanup retry.
        pass

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )
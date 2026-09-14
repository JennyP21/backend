import uuid
from uuid import UUID

from fastapi import APIRouter, HTTPException, UploadFile, status

from app.dependencies import CurrentUserId, DbSession, Storage
from app.models.document import Document
from app.schemas.document import DocumentResponse
from app.services.project import get_owned_project

router = APIRouter(
    tags=["Documents"],
)

MAX_FILE_SIZE = 30 * 1024 * 1024

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
    
    
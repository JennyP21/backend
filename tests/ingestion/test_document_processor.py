import uuid

import pytest

from app.models.document import Document
from app.services.document_processor import process_document


async def test_process_document_downloads_pdf(
    fake_storage,
):
    document_id = uuid.uuid4()
    project_id = uuid.uuid4()

    storage_key = (
        f"projects/{project_id}/"
        f"documents/{document_id}/source.pdf"
    )

    pdf_content = (
        b"%PDF-1.4 fake pdf contents"
    )

    await fake_storage.upload(
        key=storage_key,
        content=pdf_content,
        content_type="application/pdf",
    )

    document = Document(
        id=document_id,
        project_id=project_id,
        uploaded_by="user_test_123",
        original_filename="guide.pdf",
        mime_type="application/pdf",
        file_size=len(pdf_content),
        storage_key=storage_key,
        metadata_={},
    )

    await process_document(
        document=document,
        storage=fake_storage,
    )
    
async def test_process_document_rejects_empty_file(
    fake_storage,
):
    document_id = uuid.uuid4()
    project_id = uuid.uuid4()

    storage_key = (
        f"projects/{project_id}/"
        f"documents/{document_id}/source.pdf"
    )

    await fake_storage.upload(
        key=storage_key,
        content=b"",
        content_type="application/pdf",
    )

    document = Document(
        id=document_id,
        project_id=project_id,
        uploaded_by="user_test_123",
        original_filename="empty.pdf",
        mime_type="application/pdf",
        file_size=0,
        storage_key=storage_key,
        metadata_={},
    )

    with pytest.raises(
        ValueError,
        match="Downloaded document is empty",
    ):
        await process_document(
            document=document,
            storage=fake_storage,
        )
    
async def test_process_document_rejects_non_pdf_content(
    fake_storage,
):
    document_id = uuid.uuid4()
    project_id = uuid.uuid4()

    storage_key = (
        f"projects/{project_id}/"
        f"documents/{document_id}/source.pdf"
    )

    content = b"this is not actually a PDF"

    await fake_storage.upload(
        key=storage_key,
        content=content,
        content_type="application/pdf",
    )

    document = Document(
        id=document_id,
        project_id=project_id,
        uploaded_by="user_test_123",
        original_filename="fake.pdf",
        mime_type="application/pdf",
        file_size=len(content),
        storage_key=storage_key,
        metadata_={},
    )

    with pytest.raises(
        ValueError,
        match="Downloaded file is not a valid PDF",
    ):
        await process_document(
            document=document,
            storage=fake_storage,
        )
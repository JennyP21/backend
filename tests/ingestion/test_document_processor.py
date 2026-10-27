import uuid

import pytest

from app.models.document import Document
from app.parsing.base import ParsedDocument, ParsedElement
from app.services.chunking import DocumentChunker
from app.services.document_processor import process_document
from tests.conftest import fake_chunker


class FakePdfParser:
    def parse(
        self,
        content: bytes,
    ) -> ParsedDocument:
        return ParsedDocument(
            page_count=3,
            elements=[
                ParsedElement(
                    category="Title",
                    text="RAG Architecture",
                    page_number=1,
                ),
                ParsedElement(
                    category="NarrativeText",
                    text="Retrieval augmented generation...",
                    page_number=1,
                ),
                ParsedElement(
                    category="NarrativeText",
                    text="Embeddings are stored...",
                    page_number=2,
                ),
            ],
        )

async def test_process_document_downloads_pdf(
    fake_storage,
    fake_chunker
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

    chunks = await process_document(
        document=document,
        storage=fake_storage,
        parser=FakePdfParser(),
        chunker=fake_chunker,
    )
    # Document model was updated with page_count from parser
    assert document.page_count == 3
    # Returned value is a list of TextChunk objects
    assert len(chunks) == 1
    assert chunks[0].page_start == 1
    assert chunks[0].page_end == 2
    assert chunks[0].token_count > 0
    assert chunks[0].metadata_["heading_path"] == ["RAG Architecture"]
    assert "Retrieval augmented generation..." in chunks[0].content
    
async def test_process_document_rejects_empty_file(
    fake_storage,
    fake_chunker
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
            parser=FakePdfParser(),
            chunker=fake_chunker
        )
    
async def test_process_document_rejects_non_pdf_content(
    fake_storage,
    fake_chunker
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
            parser=FakePdfParser(),
            chunker=fake_chunker
        )
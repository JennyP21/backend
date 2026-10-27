from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk
from app.parsing.base import ParsedDocument, ParsedElement
from app.services.chunking import DocumentChunker, TextChunk
from app.services.document_processor import process_document


@pytest.fixture
def chunker() -> DocumentChunker:
    return DocumentChunker(
        embeddings=DeterministicFakeEmbedding(size=128),
        max_tokens=80,
        overlap_tokens=10
    )

@pytest.mark.asyncio
async def test_process_document_creates_chunk_records():
    document = Document(
        id=uuid4(),
        project_id=uuid4(),
        uploaded_by="test-clerk-user",
        original_filename="test.pdf",
        mime_type="application/pdf",
        file_size=9,
        storage_key="test.pdf",
        status=DocumentStatus.UPLOADED,
    )

    storage = Mock()
    storage.download = AsyncMock(
        return_value=b"%PDF-1.4\n"
    )

    parser = Mock()
    parser.parse.return_value = ParsedDocument(
        page_count=3,
        elements=[],
    )

    chunker = Mock()
    chunker.chunk.return_value = [
        TextChunk(
            content="Example document content",
            token_count=3,
            page_start=2,
            page_end=2,
            metadata={"heading_path": ["Introduction"]},
        )
    ]

    records = await process_document(
        document=document,
        storage=storage,
        parser=parser,
        chunker=chunker,
    )

    assert document.page_count == 3
    assert len(records) == 1

    record = records[0]

    assert isinstance(record, DocumentChunk)
    assert record.document_id == document.id
    assert record.project_id == document.project_id
    assert record.chunk_index == 0
    assert record.page_start == 2
    assert record.page_end == 2
    assert record.content == "Example document content"
    assert record.token_count == 3
    assert record.metadata_["heading_path"] == ["Introduction"]

    storage.download.assert_awaited_once_with(
        key="test.pdf"
    )
    parser.parse.assert_called_once()
    chunker.chunk.assert_called_once()

def test_narrative_chunking(chunker: DocumentChunker) -> None:
    document = ParsedDocument(
        page_count=2,
        elements=[
            ParsedElement(
                category="Title",
                text="Amazon S3",
                page_number=2,
            ),
            ParsedElement(
                category="NarrativeText",
                text=(
                    "Amazon S3 stores objects in buckets. "
                    "Bucket policies control access to stored data. "
                ) * 80,
                page_number=2,
            ),
        ],
    )
    
    chunks = chunker.chunk(document)
    
    assert len(chunks) > 1
    
    for chunk in chunks:
        assert chunk.content.strip()
        assert 0 < chunk.token_count <= 80
        assert chunk.page_start == 2
        assert chunk.page_end == 2
        assert chunk.metadata["heading_path"] == ["Amazon S3"]
        assert chunk.token_count == len(
            chunker.encoding.encode(chunk.content)
        )

def test_empty_document(chunker: DocumentChunker) -> None:
    document = ParsedDocument(
        page_count=1,
        elements=[],
    )

    assert chunker.chunk(document) == []
    
def test_table_does_not_lose_rows(chunker: DocumentChunker) -> None:
    document = ParsedDocument(
        page_count=1,
        elements=[
            ParsedElement(
                category="Table",
                text="Item ALPHA BRAVO CHARLIE",
                page_number=1,
                metadata={
                    "text_as_html": (
                        "<table>"
                        "<tr><th>Item</th></tr>"
                        "<tr><td>ALPHA</td></tr>"
                        "<tr><td>BRAVO</td></tr>"
                        "<tr><td>CHARLIE</td></tr>"
                        "</table>"
                    )
                },
            )
        ],
    )

    chunks = chunker.chunk(document)
    combined = "\n".join(chunk.content for chunk in chunks)

    assert "ALPHA" in combined
    assert "BRAVO" in combined
    assert "CHARLIE" in combined
    assert all(chunk.token_count <= 80 for chunk in chunks)
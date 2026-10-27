import asyncio

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.parsing.base import PdfParser
from app.services.chunking import DocumentChunker
from app.storage.base import StorageService

async def process_document(
    document: Document,
    storage: StorageService,
    parser: PdfParser,
    chunker: DocumentChunker
) -> list[DocumentChunk]:
    content = await storage.download(
        key=document.storage_key,
    )
    
    if not content:
        raise ValueError(
            "Downloaded document is empty"
        )
        
    if not content.startswith(b"%PDF-"):
        raise ValueError(
            "Downloaded file is not a valid PDF"
        )
    
    parsed_document = await asyncio.to_thread(
        parser.parse,
        content
    )
    
    document.page_count = (
        parsed_document.page_count
    )
    
    chunks = await asyncio.to_thread(
        chunker.chunk,
        parsed_document
    )
    
    if not chunks:
        raise ValueError("No searchable content extracted from PDF")
    
    chunk_records = [
        DocumentChunk(
            project_id=document.project_id,
            document_id=document.id,
            chunk_index=idx,
            content=chunk.content,
            token_count=chunk.token_count,
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            metadata_=chunk.metadata,
        )
        for idx, chunk in enumerate(chunks)
    ]
    
    return chunk_records
    
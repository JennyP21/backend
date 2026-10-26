import asyncio

from app.models.document import Document
from app.parsing.base import PdfParser
from app.services.chunking import DocumentChunker, TextChunk
from app.storage.base import StorageService


async def process_document(
    document: Document,
    storage: StorageService,
    parser: PdfParser,
    chunker: DocumentChunker
) -> list[TextChunk]:
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
        
    return chunks
    
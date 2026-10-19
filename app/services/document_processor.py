import asyncio
from app.models.document import Document
from app.parsing.base import ParsedDocument, PdfParser
from app.storage.base import StorageService

async def process_document(
    document: Document,
    storage: StorageService,
    parser: PdfParser
) -> ParsedDocument:
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
        
    return parsed_document
    
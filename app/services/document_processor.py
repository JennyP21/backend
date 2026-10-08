from app.models.document import Document
from app.storage.base import StorageService


async def process_document(
    document: Document,
    storage: StorageService,
) -> None:
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
    
    

from app.parsing.base import ParsedDocument, ParsedElement
from app.services.chunking import DocumentChunker


def make_element(
    text: str,
    *,
    category: str = "NarrativeText",
    page: int | None = 1,
    metadata: dict[str, object] | None = None,
) -> ParsedElement:
    return ParsedElement(
        category=category,
        text=text,
        page_number=page,
        metadata=metadata or {},
    )


def make_document(*elements: ParsedElement) -> ParsedDocument:
    return ParsedDocument(page_count=10, elements=list(elements))
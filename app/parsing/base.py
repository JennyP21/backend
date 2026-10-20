from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ParsedElement:
    category: str
    text: str
    page_number: int | None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    page_count: int
    elements: list[ParsedElement]


class PdfParser(Protocol):
    def parse(
        self,
        content: bytes,
    ) -> ParsedDocument:
        ...
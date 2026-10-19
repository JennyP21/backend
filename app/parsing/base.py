from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ParsedElement:
    category: str
    text: str
    page_number: int | None


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
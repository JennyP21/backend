from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from pypdf import PdfReader
from unstructured.partition.pdf import partition_pdf

from app.parsing.base import (
    ParsedDocument,
    ParsedElement,
)


class UnstructuredPdfParser:
    def __init__(
        self,
        *,
        strategy: str = "fast",
    ) -> None:
        self.strategy = strategy

    def parse(
        self,
        content: bytes,
    ) -> ParsedDocument:
        if not content:
            raise ValueError(
                "PDF content is empty"
            )

        try:
            reader = PdfReader(
                BytesIO(content)
            )

            page_count = len(reader.pages)

        except Exception as exc:
            raise ValueError(
                "Unable to read PDF"
            ) from exc

        if page_count == 0:
            raise ValueError(
                "PDF contains no pages"
            )

        try:
            with TemporaryDirectory() as temp_dir:
                pdf_path = (
                    Path(temp_dir)
                    / "document.pdf"
                )

                pdf_path.write_bytes(content)

                elements = partition_pdf(
                    filename=str(pdf_path),
                    strategy=self.strategy,
                )

        except Exception as exc:
            raise ValueError(
                "Unable to parse PDF"
            ) from exc

        parsed_elements: list[ParsedElement] = []

        for element in elements:
            text = str(element).strip()

            if not text:
                continue

            page_number = getattr(
                element.metadata,
                "page_number",
                None,
            )

            category = getattr(
                element,
                "category",
                type(element).__name__,
            )

            parsed_elements.append(
                ParsedElement(
                    category=str(category),
                    text=text,
                    page_number=page_number,
                )
            )

        return ParsedDocument(
            page_count=page_count,
            elements=parsed_elements,
        )
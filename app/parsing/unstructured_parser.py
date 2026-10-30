from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from pypdf import PdfReader
from unstructured.partition.pdf import partition_pdf

from app.parsing.base import ParsedDocument, ParsedElement


class UnstructuredPdfParser:
    def __init__(
        self,
        *,
        strategy,
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

            source_metadata = element.metadata
            extra_metadata: dict[str, object] = {}

            table_html = getattr(
                source_metadata, "text_as_html", None
            )
            if table_html:
                extra_metadata["text_as_html"] = table_html

            category_depth = getattr(
                source_metadata, "category_depth", None
            )
            if category_depth is not None:
                extra_metadata["category_depth"] = category_depth

            parent_id = getattr(
                source_metadata, "parent_id", None
            )
            if parent_id is not None:
                extra_metadata["parent_id"] = parent_id

            page_number = getattr(
                source_metadata, "page_number", None
            )

            category = getattr(
                element, "category", type(element).__name__
            )

            parsed_elements.append(
                ParsedElement(
                    category=str(category),
                    text=text,
                    page_number=page_number,
                    metadata=extra_metadata,
                )
            )

        return ParsedDocument(
            page_count=page_count,
            elements=parsed_elements,
        )
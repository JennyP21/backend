"""PDF structure-aware semantic chunking for RagLab."""

from dataclasses import dataclass
from html.parser import HTMLParser

from langchain_openai import OpenAIEmbeddings
import tiktoken
from langchain_core.embeddings import Embeddings
from langchain_experimental.text_splitter import SemanticChunker

from app.parsing.base import ParsedDocument, ParsedElement


@dataclass(frozen=True, slots=True)
class TextChunk:
    content: str
    token_count: int
    page_start: int | None
    page_end: int | None
    metadata: dict[str, object]

class _TableHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[tuple[str, bool]]] = []
        self._row: list[tuple[str, bool]] | None = None
        self._cell_parts: list[str] | None = None
        self._cell_is_header = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._row = []
        elif tag in {"th", "td"} and self._row is not None:
            self._cell_parts = []
            self._cell_is_header = tag == "th"
        elif tag == "br" and self._cell_parts is not None:
            self._cell_parts.append(" ")

    def handle_data(self, data: str) -> None:
        if self._cell_parts is not None:
            self._cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"th", "td"} and self._cell_parts is not None:
            text = " ".join("".join(self._cell_parts).split())

            if self._row is not None:
                self._row.append((text, self._cell_is_header))

            self._cell_parts = None

        elif tag == "tr" and self._row is not None:
            if any(text for text, _ in self._row):
                self.rows.append(self._row)

            self._row = None

class DocumentChunker:
    """Semantic narrative splitting with page/heading/table-aware metadata."""

    def __init__(
        self,
        *,
        embeddings: Embeddings | None = None,
        max_tokens: int = 500,
        overlap_tokens: int = 50,
        encoding_name: str = "cl100k_base",
    ) -> None:
        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if not 0 <= overlap_tokens < max_tokens:
            raise ValueError("overlap_tokens must be >= 0 and < max_tokens")
        
        self.overlap_tokens = overlap_tokens
        self.max_tokens = max_tokens
        self.encoding = tiktoken.get_encoding(encoding_name)
        
        if embeddings is None:
            embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        
        self._semantic_splitter = SemanticChunker(
            embeddings=embeddings,
            breakpoint_threshold_type="percentile"
        )

    def _count_tokens(self, text: str) -> int:
        return len(self.encoding.encode(text))
    
    def _hard_split(
        self,
        text: str,
        page_start: int | None,
        page_end: int | None,
        heading_path: list[str],
        extra_metadata: dict[str, object],
    ) -> list[TextChunk]:
        tokens = self.encoding.encode(text)
        list_of_text_chunk = []
        
        stride = self.max_tokens - self.overlap_tokens
        for start in range(0, len(tokens), stride):
            slice_ = tokens[start : start + self.max_tokens]
            decoded = self.encoding.decode(slice_)
            
            metadata={
                "heading_path": heading_path,
                "split_from_oversized_element": True,
                **extra_metadata,
            }
            
            list_of_text_chunk.append(
                TextChunk(
                    content=decoded,
                    token_count=len(slice_),
                    page_start=page_start,
                    page_end=page_end,
                    metadata=metadata
                )
            )
        
        
        return list_of_text_chunk
    
    def _chunk_table(
        self,
        element: ParsedElement,
        heading_path: list[str],
    ) -> list[TextChunk]:
        html = element.metadata.get("text_as_html", "")
        metadata = {
            "heading_path": heading_path,
            "is_table": True
        }
        if not html:
            return self._hard_split(element.text, element.page_number, element.page_number, heading_path, {})

        tableParser = _TableHTMLParser()
        tableParser.feed(str(html))
        
        header_rows = []
        data_rows = []
        
        for row in tableParser.rows:
            if any(is_header for _, is_header in row):
                header_rows.append(row)
            else:
                data_rows.append(row)
                
        def format_row(row):
            return " | ".join(cell_text for cell_text, _ in row)

        if not data_rows:
            if not header_rows:
                return []
            # header-only table → return it as one chunk
            content = format_row(header_rows[0])
            return [TextChunk(
                content=content,
                token_count=self._count_tokens(content),
                page_start=element.page_number,
                page_end=element.page_number,
                metadata=metadata,
            )]
        
        header_line = format_row(header_rows[0]) if header_rows else ""
        
        data_lines = [format_row(row) for row in data_rows]
        
        buffer = []
        chunks = []
        
        for line in data_lines:
            candidate = header_line + "\n" + "\n".join(buffer + [line])
            
            if self._count_tokens(candidate) > self.max_tokens and buffer:
                content = header_line + "\n" + "\n".join(buffer)
                chunks.append(
                    TextChunk(
                        content=content,
                        token_count=self._count_tokens(content),
                        page_start=element.page_number,
                        page_end=element.page_number,
                        metadata=metadata
                    )
                )
                buffer = []
            else:
                buffer.append(line)
        
        if buffer:
            content = header_line + "\n" + "\n".join(buffer)
            chunks.append(
                TextChunk(
                    content=content,
                    token_count=self._count_tokens(content),
                    page_start=element.page_number,
                    page_end=element.page_number,
                    metadata=metadata
                )
            )
        
        
        return chunks
    
    def _semantic_split(
        self, 
        content: str,
        page_start: int | None,
        page_end: int | None,
        heading_path: list[str],
    ) -> list[TextChunk]:
        docs = self._semantic_splitter.create_documents([content])
        metadata: dict[str, object] = {"heading_path": list(heading_path)}
        chunks: list[TextChunk] = []
        for doc in docs:
            text = doc.page_content.strip()

            if not text:
                continue
            
            token_count = self._count_tokens(text)
            
            if token_count <= self.max_tokens:
                chunks.append(TextChunk(
                    content=text,
                    token_count=token_count,
                    page_start=page_start,
                    page_end=page_end,
                    metadata=metadata
                ))
            else:
                chunks.extend(self._hard_split(text, page_start, page_end, heading_path, {}))
        
        return chunks

    def _flush_section(
        self,
        texts: list[str],          # accumulated text blocks from narrative elements
        page_start: int | None,
        page_end: int | None,
        heading_path: list[str],
    ) -> list[TextChunk]:
        if not texts:
            return []
        
        combined = "\n\n".join(texts)
        token_count = self._count_tokens(combined)
        metadata: dict[str, object] = {
            "heading_path": heading_path,
        }
        if token_count <= self.max_tokens:
            return [TextChunk(
                content=combined,
                token_count=token_count,
                page_start=page_start,
                page_end=page_end,
                metadata=metadata
            )]
        
        return self._semantic_split(combined, page_start, page_end, heading_path)
    
    def chunk(self, document: ParsedDocument) -> list[TextChunk]:
        chunks: list[TextChunk] = []
        texts: list[str] = []
        page_start: int | None = None
        page_end: int | None = None
        heading_path: list[str] = []
        
        for element in document.elements:               
            if element.category in {"Title", "Header"}:
                chunks.extend(self._flush_section(texts, page_start, page_end, heading_path))
                page_start = None
                category_depth = element.metadata.get("category_depth", 1)
                if category_depth == 2 and heading_path:
                    heading_path = [heading_path[0], element.text]
                else:
                    heading_path = [element.text]
                texts = []
                
            elif element.category == "Table":
                chunks.extend(self._flush_section(texts, page_start, page_end, heading_path))
                texts = []
                chunks.extend(self._chunk_table(element, heading_path))
                page_start = None
            else:
                if element.text == "":
                    continue
                if page_start == None:
                    page_start = element.page_number
                page_end = element.page_number
                texts.append(element.text)
        
        chunks.extend(self._flush_section(texts, page_start, page_end, heading_path))
        
        return chunks
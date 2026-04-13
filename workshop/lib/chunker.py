"""PDF page chunking for large documents.

Splits multi-page PDFs into batches for processing.
Target: <5s/page, chunk into batches of 20 for docs >100 pages.
"""

import io
from dataclasses import dataclass

from pypdf import PdfReader, PdfWriter


@dataclass(frozen=True)
class PageChunk:
    chunk_index: int
    start_page: int  # 1-indexed
    end_page: int    # 1-indexed, inclusive
    pdf_bytes: bytes
    page_count: int


def get_page_count(pdf_bytes: bytes) -> int:
    """Return the number of pages in a PDF."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return len(reader.pages)


def chunk_pdf(pdf_bytes: bytes, chunk_size: int = 20, max_pages_before_chunking: int = 100) -> list[PageChunk]:
    """Split a PDF into page chunks.

    If the PDF has <= max_pages_before_chunking pages, return a single chunk
    containing all pages. Otherwise split into chunks of chunk_size pages.
    """
    reader = PdfReader(io.BytesIO(pdf_bytes))
    total_pages = len(reader.pages)

    if total_pages <= max_pages_before_chunking:
        return [PageChunk(
            chunk_index=0,
            start_page=1,
            end_page=total_pages,
            pdf_bytes=pdf_bytes,
            page_count=total_pages,
        )]

    chunks = []
    for i in range(0, total_pages, chunk_size):
        writer = PdfWriter()
        end = min(i + chunk_size, total_pages)
        for page_idx in range(i, end):
            writer.add_page(reader.pages[page_idx])

        buf = io.BytesIO()
        writer.write(buf)
        chunk_bytes = buf.getvalue()

        chunks.append(PageChunk(
            chunk_index=len(chunks),
            start_page=i + 1,
            end_page=end,
            pdf_bytes=chunk_bytes,
            page_count=end - i,
        ))

    return chunks


def extract_single_page(pdf_bytes: bytes, page_num: int) -> bytes:
    """Extract a single page (1-indexed) from a PDF as a new PDF."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    writer.add_page(reader.pages[page_num - 1])
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()

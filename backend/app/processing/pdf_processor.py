"""PDF document processor - extracts pages, text, and tables."""

import io
from pathlib import Path
from typing import Any, Optional

from loguru import logger
from PIL import Image


class PDFProcessor:
    """Handles PDF parsing, page extraction, and text extraction."""

    async def extract_pages(self, pdf_bytes: bytes) -> list[dict[str, Any]]:
        """Extract all pages from a PDF as images and text."""
        import pdfplumber

        pages = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for i, page in enumerate(pdf.pages):
                page_data = {
                    "page_number": i + 1,
                    "width": int(page.width),
                    "height": int(page.height),
                    "text": page.extract_text() or "",
                    "tables": [],
                }

                # Extract tables
                try:
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            if table and len(table) > 0:
                                headers = table[0] if table[0] else []
                                rows = table[1:] if len(table) > 1 else []
                                page_data["tables"].append(
                                    {
                                        "headers": [
                                            h.strip() if h else ""
                                            for h in headers
                                        ],
                                        "rows": [
                                            [
                                                cell.strip() if cell else ""
                                                for cell in row
                                            ]
                                            for row in rows
                                        ],
                                    }
                                )
                except Exception as e:
                    logger.warning(f"Table extraction failed on page {i + 1}: {e}")

                pages.append(page_data)

        return pages

    async def pdf_to_images(self, pdf_bytes: bytes, dpi: int = 300) -> list[Image.Image]:
        """Convert PDF pages to PIL Images."""
        try:
            from pdf2image import convert_from_bytes

            images = convert_from_bytes(pdf_bytes, dpi=dpi)
            return images
        except Exception as e:
            logger.error(f"PDF to image conversion failed: {e}")
            return []

    async def get_page_count(self, pdf_bytes: bytes) -> int:
        """Get the number of pages in a PDF."""
        import pdfplumber

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            return len(pdf.pages)

    async def extract_metadata(self, pdf_bytes: bytes) -> dict[str, Any]:
        """Extract PDF metadata."""
        import pdfplumber

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            return dict(pdf.metadata) if pdf.metadata else {}


pdf_processor = PDFProcessor()

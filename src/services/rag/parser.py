"""
Document Parser and Text Extraction module.
Extracts clean textual content from supported file formats (.txt, .md, .pdf).
"""

import io
from pypdf import PdfReader


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extracts text content from a PDF file byte stream using pypdf.

    Args:
        file_bytes: Raw binary bytes of the PDF.

    Returns:
        Extracted text formatted with page headings.
    """
    reader = PdfReader(io.BytesIO(file_bytes))
    extracted_pages: list[str] = []
    for idx, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            extracted_pages.append(f"--- Page {idx + 1} ---\n{text.strip()}")

    if not extracted_pages:
        raise ValueError("The uploaded PDF does not contain extractable text (it may be scanned or empty).")

    return "\n\n".join(extracted_pages)


def extract_text_from_file(filename: str, file_bytes: bytes) -> str:
    """
    Extracts text from uploaded file bytes according to file extension (.txt, .md, .pdf).

    Args:
        filename: Name of the file with extension.
        file_bytes: Raw binary bytes of the file.

    Returns:
        Extracted string content of the document.
    """
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if ext == "pdf":
        return extract_text_from_pdf(file_bytes)
    return file_bytes.decode("utf-8", errors="replace")

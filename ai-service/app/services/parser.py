import re
from typing import List, Dict, Any
import logging

from pypdf import PdfReader

logger = logging.getLogger(__name__)


def parse_pdf(file_path: str) -> List[Dict[str, Any]]:
    """
    Parse a PDF file and return a list of pages.

    Returns:
        List of dicts: [{"page_number": 1, "text": "..."}, ...]
    """
    pages = []
    try:
        reader = PdfReader(file_path)
        for i, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            # Normalize whitespace
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                pages.append({
                    "page_number": i,
                    "text": text
                })
        logger.info(f"Parsed {len(pages)} pages from {file_path}")
        return pages
    except Exception as e:
        logger.error(f"Failed to parse PDF {file_path}: {e}")
        raise


def parse_text_file(file_path: str) -> List[Dict[str, Any]]:
    """Parse plain text files (fallback for .txt, .md, etc.)."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return [{"page_number": 1, "text": text}]
    except Exception as e:
        logger.error(f"Failed to parse text file {file_path}: {e}")
        raise


def parse_document(file_path: str) -> List[Dict[str, Any]]:
    """Route to the correct parser based on file extension."""
    if file_path.lower().endswith(".pdf"):
        return parse_pdf(file_path)
    elif file_path.lower().endswith((".txt", ".md")):
        return parse_text_file(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_path}")

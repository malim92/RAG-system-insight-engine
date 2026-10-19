from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def chunk_pages(
    pages: List[Dict[str, Any]],
    chunk_size: int = 512,
    chunk_overlap: int = 50
) -> List[Dict[str, Any]]:
    """
    Split parsed pages into overlapping chunks of a target size (in characters).

    Strategy: recursive character splitting with page-boundary awareness.
    For a production system you would graduate to semantic chunking
    (splitting on section headings, sentences, or embeddings), but character
    chunking with overlap is the correct baseline.

    Args:
        pages: [{"page_number": int, "text": str}, ...]
        chunk_size: target characters per chunk
        chunk_overlap: overlap between consecutive chunks (improves retrieval recall)

    Returns:
        List of dicts: [{"chunk_index": int, "text": str, "page_number": int}, ...]
    """
    chunks = []
    chunk_index = 0

    for page in pages:
        text = page["text"]
        start = 0
        text_len = len(text)

        while start < text_len:
            end = min(start + chunk_size, text_len)

            # Try to break at a sentence or word boundary near the target size
            if end < text_len:
                window = text[start:end]
                # Look for the last sentence-ending punctuation
                for punct in [". ", ".\n", "! ", "? "]:
                    last_punct = window.rfind(punct)
                    if last_punct > chunk_size * 0.5:
                        end = start + last_punct + 1
                        break
                else:
                    # No sentence boundary found — break at last space
                    last_space = window.rfind(" ")
                    if last_space > chunk_size * 0.5:
                        end = start + last_space

            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({
                    "chunk_index": chunk_index,
                    "text": chunk_text,
                    "page_number": page["page_number"]
                })
                chunk_index += 1

            # Advance with overlap (avoid infinite loop on tiny pages)
            advance = end - start - chunk_overlap
            if advance <= 0:
                advance = chunk_size
            start += advance

    logger.info(f"Created {len(chunks)} chunks from {len(pages)} pages")
    return chunks

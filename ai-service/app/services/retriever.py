import logging
from typing import List, Dict, Any

from app.config import get_settings
from app.services.embedder import get_embedder
from app.services.qdrant_store import get_client

logger = logging.getLogger(__name__)
settings = get_settings()


async def retrieve(question: str, tenant_id: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Embed the question and find the most semantically similar chunks.

    CRITICAL: the query_vector must come from the SAME embedding model that
    stored the chunks — vectors from different models are incomparable
    (different semantic spaces). This is why embedder.py is a shared singleton.

    The payload filter scopes the search to one tenant: even if another
    tenant's chunk is numerically close, it can never be returned.
    """
    embedder = get_embedder()
    query_vector = (await embedder.embed([question]))[0]

    client = get_client()
    results = client.search(
        collection_name=settings.qdrant_collection,
        query_vector=query_vector,
        query_filter={
            "must": [
                {"key": "tenant_id", "match": {"value": tenant_id}}
            ]
        },
        limit=top_k,
        with_payload=True,
    )

    chunks = []
    for r in results:
        chunks.append({
            "score": r.score,
            "text": r.payload["text"],
            "document_id": r.payload["document_id"],
            "chunk_index": r.payload["chunk_index"],
            "page_number": r.payload["page_number"],
        })

    for i, c in enumerate(chunks):
        preview = c["text"][:120].replace("\n", " ")
        logger.info(
            f"  [{i + 1}] score={c['score']:.3f} "
            f"doc={c['document_id'][:8]} chunk={c['chunk_index']}: {preview}..."
        )

    logger.info(f"Retrieved {len(chunks)} chunks for tenant={tenant_id}")
    return chunks

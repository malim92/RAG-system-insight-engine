from typing import List, Dict, Any
import logging
import uuid as uuidlib
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from app.config import get_settings
from app.services.embedder import VECTOR_SIZE

logger = logging.getLogger(__name__)
settings = get_settings()

# VECTOR_SIZE is defined in the embedder module — the dimension is a property
# of whatever embedding model is active, so it lives next to that model.


def _point_id(document_id: str, chunk_index: int) -> str:
    """
    Derive a deterministic UUIDv5 from (document_id, chunk_index).

    Why not just use "docid:chunkindex" as the ID? Qdrant only accepts
    unsigned integers or UUIDs as point IDs — composite strings are rejected.

    Why uuid5 instead of uuid4? uuid5 is deterministic: the same
    (document_id, chunk_index) always produces the same UUID. That makes
    upserts idempotent — re-ingesting a document overwrites its existing
    points instead of creating duplicates.
    """
    return str(uuidlib.uuid5(uuidlib.NAMESPACE_URL, f"{document_id}:{chunk_index}"))


def get_client() -> QdrantClient:
    """Create a Qdrant client. Each call is cheap; the client doesn't need pooling."""
    return QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)


def ensure_collection(client: QdrantClient, collection_name: str):
    """Create the collection if it doesn't exist yet."""
    existing = [c.name for c in client.get_collections().collections]
    if collection_name not in existing:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        logger.info(f"Created Qdrant collection: {collection_name}")


def upsert_chunks(
    client: QdrantClient,
    collection_name: str,
    document_id: str,
    tenant_id: str,
    chunks: List[Dict[str, Any]],
    embeddings: List[List[float]],
):
    """
    Store chunk embeddings in Qdrant with metadata payloads.

    Every point carries the tenant_id as a payload field so we can
    filter by tenant at query time (data isolation).
    """
    points = []
    for chunk, embedding in zip(chunks, embeddings):
        points.append(PointStruct(
            id=_point_id(document_id, chunk["chunk_index"]),
            vector=embedding,
            payload={
                "document_id": document_id,
                "tenant_id": tenant_id,
                "chunk_index": chunk["chunk_index"],
                "text": chunk["text"],
                "page_number": chunk["page_number"],
            }
        ))

    client.upsert(collection_name=collection_name, points=points)
    logger.info(f"Upserted {len(points)} vectors for document {document_id}")

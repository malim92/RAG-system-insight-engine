import json
import logging
import time
import asyncio
import httpx
from redis import Redis

from app.config import get_settings
from app.services.parser import parse_document
from app.services.chunker import chunk_pages
from app.services.embedder import get_embedder
from app.services.qdrant_store import get_client, ensure_collection, upsert_chunks

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()
DOCUMENT_QUEUE = "document:queue"


def get_redis() -> Redis:
    return Redis(host=settings.redis_host, port=settings.redis_port, decode_responses=True)


def notify_backend(document_id: str, status: str, error_message: str = None):
    """Tell Spring Boot the document is done (or failed)."""
    try:
        with httpx.Client(timeout=10) as client:
            client.post(
                f"{settings.backend_url}/api/documents/{document_id}/status",
                json={
                    "status": status,
                    "errorMessage": error_message
                }
            )
        logger.info(f"Notified backend: document={document_id} status={status}")
    except Exception as e:
        logger.error(f"Failed to notify backend for {document_id}: {e}")


async def process_job(job_data: dict):
    document_id = job_data["documentId"]
    stored_path = job_data["storedPath"]
    tenant_id = job_data["tenantId"]
    original_name = job_data["originalName"]

    logger.info(f"Processing document {document_id}: {original_name}")
    notify_backend(document_id, "PROCESSING")

    try:
        # 1. Parse
        pages = parse_document(stored_path)

        # 2. Chunk
        chunks = chunk_pages(pages, chunk_size=512, chunk_overlap=50)
        if not chunks:
            raise ValueError("No text extracted from document")

        # 3. Embed (batched)
        texts = [c["text"] for c in chunks]
        embeddings = await get_embedder().embed(texts)

        # 4. Store in Qdrant
        qdrant = get_client()
        ensure_collection(qdrant, settings.qdrant_collection)
        logger.info(f" xxx document_id={document_id}, tenant_id={tenant_id}, chunks={len(chunks)}")
        upsert_chunks(
            client=qdrant,
            collection_name=settings.qdrant_collection,
            document_id=document_id,
            tenant_id=tenant_id,
            chunks=chunks,
            embeddings=embeddings,
        )

        # 5. Notify success
        notify_backend(document_id, "COMPLETED")

    except Exception as e:
        logger.error(f"Document {document_id} failed: {e}", exc_info=True)
        notify_backend(document_id, "FAILED", str(e))


def main():
    redis = get_redis()
    logger.info("Worker started. Waiting for jobs on queue: %s", DOCUMENT_QUEUE)

    while True:
        # BRPOP blocks until a job appears (no busy polling)
        result = redis.brpop(DOCUMENT_QUEUE, timeout=5)
        if result is None:
            continue  # timeout, loop again

        queue_name, job_json = result
        try:
            job_data = json.loads(job_json)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid job payload: {e}")
            continue

        asyncio.run(process_job(job_data))


if __name__ == "__main__":
    main()

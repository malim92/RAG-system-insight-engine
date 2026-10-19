import asyncio
import logging
from functools import lru_cache
from typing import List, Protocol

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# all-MiniLM-L6-v2: 384-dim vectors, runs on CPU, ~90MB download on first use.
# Swap notes:
#   - Never mix vectors from different models in one collection.
#   - Switching models = wipe the collection and re-ingest everything.
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
VECTOR_SIZE = 384


class EmbeddingProvider(Protocol):
    """
    Contract for pluggable embedding backends.

    Anything that can turn a list of texts into a list of vectors
    satisfies this interface — local models, OpenAI API, Cohere, etc.
    The rest of the system (worker, query API) depends only on this
    contract, never on a concrete provider.
    """

    async def embed(self, texts: List[str]) -> List[List[float]]: ...


class SentenceTransformerProvider:
    """Local embedding model via sentence-transformers (HuggingFace)."""

    def __init__(self, model_name: str = EMBEDDING_MODEL):
        # Model loads once per process; encode() is thread-safe.
        self.model = SentenceTransformer(model_name)
        logger.info(f"Loaded embedding model: {model_name} (dim={VECTOR_SIZE})")

    async def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        # encode() is CPU-bound and synchronous — run it in the default
        # thread pool so it doesn't block the asyncio event loop.
        loop = asyncio.get_running_loop()
        embeddings = await loop.run_in_executor(
            None,
            lambda: self.model.encode(texts, convert_to_numpy=True),
        )
        logger.info(f"Generated {len(embeddings)} embeddings locally")
        return embeddings.tolist()


@lru_cache
def get_embedder() -> EmbeddingProvider:
    """
    Return the process-wide embedding provider.

    lru_cache makes this a singleton: the model (90MB) loads once and is
    reused across all calls. The return type is the Protocol, so callers
    are decoupled from the concrete implementation.
    """
    return SentenceTransformerProvider()

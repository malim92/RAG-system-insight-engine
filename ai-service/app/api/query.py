import json
import logging
from fastapi import APIRouter, HTTPException
from google.genai import errors as genai_errors

from app.schemas import QueryRequest, QueryResponse, Citation, ErrorResponse
from app.services.retriever import retrieve
from app.services.generator import get_answer_provider

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    """
    The RAG loop: retrieve → generate → cite.

    1. Embed the question with the SAME model used at ingestion
       (mixing embedding models breaks semantic comparability).
    2. Search Qdrant, filtered to the caller's tenant.
    3. Build numbered context blocks; the LLM cites them by number.
    4. Map the citation numbers back to real chunk metadata so the
       UI can show "source: page 3" rather than a hallucinated reference.
    """
    try:
        chunks = await retrieve(req.question, req.tenant_id)
    except Exception as e:
        logger.error(f"Retrieval failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {e}")

    if not chunks:
        return QueryResponse(
            answer="I don't have enough information in the uploaded documents to answer that.",
            citations=[],
        )

    # Numbered blocks — the [n] markers are what the LLM will cite.
    context_blocks = [
        f"[{i + 1}] (page {c['page_number']}) {c['text']}"
        for i, c in enumerate(chunks)
    ]

    try:
        answer = await get_answer_provider().answer(req.question, context_blocks)
    except RuntimeError as e:
        # Provider misconfiguration (e.g. missing API key) — not retryable
        raise HTTPException(status_code=503, detail=str(e))
    except genai_errors.APIError as e:
        # Upstream LLM failure (e.g. Gemini 503 UNAVAILABLE under high
        # demand). Pass the provider's message through VERBATIM so the
        # caller can see the real cause, and use a retryable status code.
        logger.warning(f"LLM API error: {e}")
        # error_data = json.loads(str(e.message))

        raise HTTPException(status_code=503, detail=e.message)
    except Exception as e:
        logger.error(f"Generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"{type(e).__name__}: {e}"
        )
 
    citations = [
        Citation(
            document_id=c["document_id"],
            chunk_index=c["chunk_index"],
            page_number=c["page_number"],
            score=c["score"],
        )
        for c in chunks
    ]

    return QueryResponse(answer=answer, citations=citations)

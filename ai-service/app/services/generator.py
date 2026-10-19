import asyncio
import logging
from functools import lru_cache
from typing import List, Protocol

import httpx
from openai import AsyncOpenAI
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Low temperature: RAG answers must be faithful to retrieved context,
# not creative. High temperature increases hallucination risk.
TEMPERATURE = 0.1

SYSTEM_PROMPT = """You are a precise assistant that answers questions using ONLY the provided context.

Rules:
1. Answer using only the context below. Never use outside knowledge.
2. If the context doesn't contain the answer, say exactly:
   "I don't have enough information in the uploaded documents to answer that."
3. Cite sources inline using the reference numbers like [1], [2].
4. Be concise. Bullet points only when listing multiple items."""


def build_user_prompt(question: str, context_blocks: List[str]) -> str:
    context = "\n\n".join(context_blocks)
    return f"Context:\n{context}\n\nQuestion: {question}"


class AnswerProvider(Protocol):
    """Contract for pluggable answer generation (Ollama, OpenAI, ...)."""

    async def answer(self, question: str, context_blocks: List[str]) -> str: ...


class OllamaProvider:
    """
    Local LLM via Ollama — free, offline, private.

    Ollama exposes an OpenAI-compatible API on localhost:11434, so the
    request shape is nearly identical to the OpenAI provider.
    """

    def __init__(self):
        self.base_url = settings.ollama_url.rstrip("/")
        self.model = settings.ollama_model

    async def answer(self, question: str, context_blocks: List[str]) -> str:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": self.model,
                    "temperature": TEMPERATURE,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": build_user_prompt(question, context_blocks),
                        },
                    ],
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            logger.info(f"Generated answer via Ollama ({self.model})")
            return content


class OpenAIProvider:
    def __init__(self):
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY not configured")
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def answer(self, question: str, context_blocks: List[str]) -> str:
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=TEMPERATURE,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": build_user_prompt(question, context_blocks),
                },
            ],
        )
        content = response.choices[0].message.content
        logger.info(
            f"Generated answer via OpenAI ({response.usage.total_tokens} tokens)"
        )
        return content


class GeminiProvider:
    """
    Google Gemini via the official google-genai SDK (free tier).
    Uses the ASYNC client (client.aio) so the blocking network call
    doesn't freeze the asyncio event loop.
    NOTE: no google_search tool here, deliberately. RAG's contract is
    "answer only from retrieved context" — giving the model live web
    access would silently bypass the knowledge base, break citations,
    and make evaluation meaningless.
    """

    def __init__(self):
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY not configured")
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_model

    async def answer(self, question: str, context_blocks: List[str]) -> str:
        return await self._generate_with_retry(question, context_blocks)

    async def _generate_with_retry(
        self,
        question: str,
        context_blocks: List[str],
        max_attempts: int = 4,
        base_delay: float = 2.0,
    ) -> str:
        """
        Retry Gemini calls on transient ServerError (503 high-demand) with
        exponential backoff: 2s, 4s, 8s between attempts.

        Only ServerError is retried — 4xx client errors (bad key, invalid
        request) fail immediately because retrying can't fix them. This
        distinction (transient vs. permanent failure) is what makes a
        retry policy safe: blind retries on permanent errors waste quota
        and add latency without any chance of success.
        """
        for attempt in range(1, max_attempts + 1):
            try:
                response = await self.client.aio.models.generate_content(
                    model=self.model,
                    contents=build_user_prompt(question, context_blocks),
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=TEMPERATURE,
                    ),
                )
                if attempt > 1:
                    logger.info(f"Gemini call succeeded on attempt {attempt}")
                return response.text

            except genai_errors.ServerError as e:
                if attempt == max_attempts:
                    logger.error(f"Gemini still unavailable after {max_attempts} attempts")
                    raise
                delay = base_delay * (2 ** (attempt - 1))
                logger.warning(
                    f"Gemini 503 (attempt {attempt}/{max_attempts}), "
                    f"retrying in {delay:.0f}s"
                )
                await asyncio.sleep(delay)

        raise RuntimeError("unreachable")  # for type-checkers; loop always returns or raises


@lru_cache
def get_answer_provider() -> AnswerProvider:
    """
    Factory: pick the LLM backend from configuration.

    Switching providers = changing one env var (LLM_PROVIDER=ollama|openai),
    which is the entire point of hiding them behind the AnswerProvider protocol.
    """
    provider = settings.llm_provider.lower()
    if provider == "ollama":
        logger.info(f"Using Ollama provider ({settings.ollama_model})")
        return OllamaProvider()
    elif provider == "openai":
        logger.info("Using OpenAI provider")
        return OpenAIProvider()
    elif provider == "gemini":
        logger.info(f"Using Gemini provider ({settings.gemini_model})")
        return GeminiProvider()

    else:
        raise ValueError(f"Unknown LLM provider: {provider}. Use 'ollama' or 'openai'.")

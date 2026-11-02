# build prompt, call LLM, return answer
import logging
from openai import OpenAI

from app.config import settings
from app.services.errors import UpstreamProviderError

logger = logging.getLogger(__name__)

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


def generate_answer(question: str, chunks: list[dict]) -> str:
    """Answer a question using only the provided chunks.

    Builds a grounding prompt and calls the chat completion SDK directly.
    Returns the answer text. The model is instructed to answer only from the
    chunks and to say the documents do not cover the question if they don't.
    """
    context = "\n\n".join(
        f"[{index + 1}] {chunk['text']}" for index, chunk in enumerate(chunks)
    )
    prompt = (
        "Answer the question using ONLY the provided document chunks. "
        "Do not use outside knowledge. "
        "If the chunks do not contain enough information to answer, "
        "say that the documents do not cover the question.\n\n"
        f"Question: {question}\n\nChunks:\n{context}"
    )
    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=settings.CHAT_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        # Log error type and operation only; never the exception message,
        # which could contain prompt content or API key fragments.
        logger.error(
            "upstream provider failed",
            extra={"operation": "chat", "exc_type": type(exc).__name__},
        )
        raise UpstreamProviderError("chat", exc) from exc

# build prompt, call LLM, return answer
import logging
from openai import OpenAI

from app.config import settings
from app.services.errors import UpstreamProviderError

logger = logging.getLogger(__name__)

_chat_client: OpenAI | None = None


def _get_chat_client() -> OpenAI:
    global _chat_client
    if _chat_client is None:
        _chat_client = OpenAI(
            api_key=settings.CHAT_API_KEY or settings.OPENAI_API_KEY,
            base_url=settings.CHAT_BASE_URL,
        )
    return _chat_client


ANSWERABILITY_SYSTEM = (
    "You decide whether passages contain the answer to a question. "
    "Reply with exactly one word: YES if the passages state the answer, "
    "NO otherwise. Do not explain."
)


def check_answerable(question: str, chunks: list[dict]) -> bool:
    """Decide whether the retrieved chunks contain the answer to the question.

    Makes one chat call with temperature 0. Parses strictly: strips whitespace
    and uppercases the reply; only exactly "YES" continues to generation.
    Anything else (NO, empty, prose, other text) returns False (fail closed).
    """
    context = "\n\n".join(
        f"[{index + 1}] {chunk['text']}" for index, chunk in enumerate(chunks)
    )
    user = f"Question: {question}\n\nPassages:\n{context}"
    try:
        client = _get_chat_client()
        response = client.chat.completions.create(
            model=settings.CHAT_MODEL,
            temperature=0,
            messages=[
                {"role": "system", "content": ANSWERABILITY_SYSTEM},
                {"role": "user", "content": user},
            ],
        )
        reply = (response.choices[0].message.content or "").strip().upper()
        return reply == "YES"
    except Exception as exc:
        logger.error(
            "upstream provider failed",
            extra={"operation": "chat", "exc_type": type(exc).__name__},
        )
        raise UpstreamProviderError("chat", exc) from exc


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
        client = _get_chat_client()
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

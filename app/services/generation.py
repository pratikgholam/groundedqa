# build prompt, call LLM, return answer
import logging
from openai import OpenAI

from app.config import settings
from app.services.errors import UpstreamProviderError

logger = logging.getLogger(__name__)

_client: OpenAI | None = None
_chat_client: OpenAI | None = None

# nomic-embed-text requires a task prefix so the model knows whether it is
# embedding a stored document or a user query. The prefix is applied only to the
# text sent to the provider; the stored chunk text is never modified. Keeping
# the prefix logic here (the single embedding call path) means ingestion and
# retrieval always use matching prefixes and cannot drift apart.
DOCUMENT_PREFIX = "search_document: "
QUERY_PREFIX = "search_query: "


def _prepare(texts: list[str], task: str) -> list[str]:
    prefix = DOCUMENT_PREFIX if task == "document" else QUERY_PREFIX
    return [prefix + text for text in texts]


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=settings.EMBEDDING_API_KEY,
            base_url=settings.EMBEDDING_BASE_URL,
        )
    return _client


def _get_chat_client() -> OpenAI:
    global _chat_client
    if _chat_client is None:
        _chat_client = OpenAI(
            api_key=settings.CHAT_API_KEY,
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


def embed_texts(texts: list[str], task: str = "document") -> list[list[float]]:
    """Embed a list of texts using the OpenAI embedding SDK directly.

    Inputs are batched (_BATCH_SIZE at a time) so large documents stay within
    the provider's per-request input limits. Each text is prefixed according to
    its task ("document" for stored chunks, "query" for questions) before being
    sent to the provider.
    """
    if not texts:
        return []
    try:
        client = _get_client()
        embeddings: list[list[float]] = []
        prepared = _prepare(texts, task)
        for start in range(0, len(prepared), _BATCH_SIZE):
            batch = prepared[start : start + _BATCH_SIZE]
            response = client.embeddings.create(
                model=settings.EMBEDDING_MODEL, input=batch
            )
            embeddings.extend(item.embedding for item in response.data)
        return embeddings
    except Exception as exc:
        # Log error type and operation only; never the exception message,
        # which could contain request content or API key fragments.
        logger.error(
            "upstream provider failed",
            extra={"operation": "embeddings", "exc_type": type(exc).__name__},
        )
        raise UpstreamProviderError("embeddings", exc) from exc


def embed_text(text: str, task: str = "query") -> list[float]:
    return embed_texts([text], task=task)[0]


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

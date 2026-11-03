# call the embedding provider
import logging
from openai import OpenAI

from app.config import settings
from app.services.errors import UpstreamProviderError

logger = logging.getLogger(__name__)

_client: OpenAI | None = None

_BATCH_SIZE = 100

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

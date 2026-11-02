# call the embedding provider
import logging
from openai import OpenAI

from app.config import settings
from app.services.errors import UpstreamProviderError

logger = logging.getLogger(__name__)

_client: OpenAI | None = None

_BATCH_SIZE = 100


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts using the OpenAI embedding SDK directly.

    Inputs are batched (_BATCH_SIZE at a time) so large documents stay within
    the provider's per-request input limits.
    """
    if not texts:
        return []
    try:
        client = _get_client()
        embeddings: list[list[float]] = []
        for start in range(0, len(texts), _BATCH_SIZE):
            batch = texts[start : start + _BATCH_SIZE]
            response = client.embeddings.create(model=settings.EMBEDDING_MODEL, input=batch)
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


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]

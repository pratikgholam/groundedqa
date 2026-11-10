# split text into overlapping chunks
def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    """Split text into overlapping chunks of roughly `size` characters.

    Character-based sliding window; deterministic and dependency-free.
    Returns [] for empty/whitespace-only text.
    """
    if size <= 0:
        raise ValueError("chunk size must be positive")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must be >= 0 and smaller than size")

    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0
    total = len(text)
    while start < total:
        end = min(start + size, total)
        chunks.append(text[start:end])
        if end >= total:
            break
        start = end - overlap
    return chunks

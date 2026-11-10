# PDF/text → raw text
import os
from io import BytesIO

import pypdf


def extract_text(filename: str, content: bytes) -> str:
    """Extract raw text from an uploaded file.

    Supports .txt, .md (decoded as UTF-8) and .pdf (pypdf). Any decode or
    parse failure (including pypdf.errors.PyPdfError) is converted to
    ValueError so the router can return 415 instead of a 500.
    """
    ext = os.path.splitext(filename or "")[1].lower()
    try:
        if ext in {".txt", ".md"}:
            return content.decode("utf-8")
        if ext == ".pdf":
            reader = pypdf.PdfReader(BytesIO(content))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise ValueError(
            f"Could not extract text from {filename or 'upload'}: {exc}"
        ) from exc
    raise ValueError(f"Unsupported file type: {ext or '(none)'}")

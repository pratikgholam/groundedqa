from app.services.chunking import chunk_text


def test_chunking_splits_with_overlap():
    text = "a" * 100
    chunks = chunk_text(text, size=30, overlap=5)
    assert chunks == [text[i : i + 30] for i in (0, 25, 50, 75)]
    # consecutive chunks overlap by `overlap` characters
    assert chunks[0][-5:] == chunks[1][:5]


def test_chunking_empty_and_whitespace():
    assert chunk_text("", 30, 5) == []
    assert chunk_text("   \n  ", 30, 5) == []


def test_chunking_shorter_than_size():
    assert chunk_text("hi", 30, 5) == ["hi"]


def test_chunking_exact_size():
    text = "a" * 30
    assert chunk_text(text, size=30, overlap=5) == [text]


def test_chunking_invalid_args():
    import pytest

    with pytest.raises(ValueError):
        chunk_text("hi", 0, 0)
    with pytest.raises(ValueError):
        chunk_text("hi", 10, 10)

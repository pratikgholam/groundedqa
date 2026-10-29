from app.services.extraction import extract_text


def test_txt():
    assert extract_text("notes.txt", b"hello world") == "hello world"


def test_md():
    assert extract_text("readme.md", b"# hi") == "# hi"


def test_unsupported_type_raises():
    import pytest

    with pytest.raises(ValueError):
        extract_text("image.png", b"\x89PNG")


def test_txt_non_utf8_raises_valueerror():
    import pytest

    with pytest.raises(ValueError):
        extract_text("notes.txt", b"\xff\xfe invalid utf-8")


def test_pdf_corrupt_raises_valueerror(monkeypatch):
    import pytest

    import pypdf.errors

    class BoomReader:
        def __init__(self, file):
            raise pypdf.errors.PyPdfError("broken pdf")

    monkeypatch.setattr("app.services.extraction.pypdf.PdfReader", BoomReader)
    with pytest.raises(ValueError):
        extract_text("doc.pdf", b"not a pdf")


def test_pdf_via_mocked_reader(monkeypatch):
    class FakePage:
        def extract_text(self):
            return "page one"

    class FakeReader:
        def __init__(self, file):
            self.pages = [FakePage(), FakePage()]

    monkeypatch.setattr("app.services.extraction.pypdf.PdfReader", FakeReader)
    result = extract_text("doc.pdf", b"fake pdf bytes")
    assert result == "page one\npage one"

import io
import pytest
import fitz  # PyMuPDF
from app.services.pdf_service import extract_text_from_pdf, extract_metadata_from_pdf


@pytest.fixture
def sample_pdf_bytes():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Hello scientific world. This is page one.")
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()


def test_extract_text_returns_pages(sample_pdf_bytes):
    pages = extract_text_from_pdf(sample_pdf_bytes)
    assert len(pages) == 1
    assert pages[0]["page_number"] == 1
    assert "Hello scientific world" in pages[0]["text"]


def test_extract_metadata_returns_dict(sample_pdf_bytes):
    meta = extract_metadata_from_pdf(sample_pdf_bytes)
    assert isinstance(meta, dict)
    assert "title" in meta
    assert "authors" in meta
    assert "year" in meta


def test_broken_pdf_raises():
    with pytest.raises(ValueError, match="Ungültiges PDF"):
        extract_text_from_pdf(b"this is not a pdf")


def test_empty_pdf_returns_empty_list():
    # A PDF with one blank page (no text) should yield an empty list
    doc = fitz.open()
    doc.new_page()  # blank page — fitz requires at least one page to save
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    pages = extract_text_from_pdf(buf.read())
    assert pages == []


def test_extract_doi_from_text():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Title: Test Paper\nDOI: 10.1038/nature12345\nAbstract: ...")
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    meta = extract_metadata_from_pdf(buf.read())
    assert meta["doi"] == "10.1038/nature12345"


def test_extract_doi_from_url_form():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Available at https://doi.org/10.1016/j.cell.2023.01.001")
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    meta = extract_metadata_from_pdf(buf.read())
    assert meta["doi"] == "10.1016/j.cell.2023.01.001"


def test_no_doi_returns_empty_string(sample_pdf_bytes):
    meta = extract_metadata_from_pdf(sample_pdf_bytes)
    assert meta["doi"] == ""

from app.schemas import MatrixRow, MatrixFilters, MatrixResponse

def test_matrix_schemas_importable():
    row = MatrixRow(
        source_id=1, source_title="Test", authors="", year=None, doi="", journal="",
        source_review_status="unreviewed", finding_id=None, finding_statement=None,
        finding_page_start=None, finding_page_end=None, evidence_quote=None,
        validation_status=None, validation_method=None, validation_score=None,
        finding_review_status=None, finding_review_comment=None, confidence_user=None,
        summary_short=None, summary_review_status=None, tags=[], notes_count=0,
        created_at=None, updated_at=None,
    )
    assert row.source_id == 1
    assert row.finding_id is None

def test_matrix_response_structure():
    resp = MatrixResponse(items=[], total=0, limit=100, offset=0, filters_applied={})
    assert resp.total == 0

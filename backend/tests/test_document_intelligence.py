import io

from app.core.document_intelligence import extract_from_text


def _upload(admin_client, filename, content: bytes, content_type="text/plain"):
    resp = admin_client.post(
        "/files/upload",
        files={"file": (filename, io.BytesIO(content), content_type)},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


TRIAL_BALANCE_TEXT = b"""Acme Corp Trial Balance
Period ending March 31, 2026

Total Revenue: $1,234,567
Net Income: $234,000
Total Assets: $5,678,900
Total Liabilities: ($1,200,000)
Cash and Cash Equivalents: $300,500

Report date: 2026-04-15
"""


# --- pure extraction function -------------------------------------------


def test_extract_from_text_finds_labeled_figures():
    result = extract_from_text(TRIAL_BALANCE_TEXT.decode())
    assert result["status"] == "success"
    assert result["labeled_figures"]["total_revenue"] == "1234567"
    assert result["labeled_figures"]["net_income"] == "234000"
    assert result["labeled_figures"]["total_assets"] == "5678900"
    # Parenthesized amount is a negative number.
    assert result["labeled_figures"]["total_liabilities"] == "-1200000"


def test_extract_from_text_finds_dates():
    result = extract_from_text(TRIAL_BALANCE_TEXT.decode())
    assert "2026-04-15" in result["dates"]
    assert any("March 31, 2026" in d or d == "March 31, 2026" for d in result["dates"])


def test_extract_from_text_empty_input_status():
    result = extract_from_text("just some prose with no figures or dates in it at all")
    assert result["status"] == "empty"
    assert result["amounts"] == []
    assert result["dates"] == []


# --- route-level ----------------------------------------------------------


def test_extract_endpoint_runs_against_uploaded_txt(admin_client):
    record = _upload(admin_client, "trial_balance.txt", TRIAL_BALANCE_TEXT)

    resp = admin_client.post(f"/files/{record['id']}/extract")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "success"
    assert body["file_record_id"] == record["id"]
    assert body["labeled_figures"]["total_revenue"] == "1234567"
    assert body["extracted_by_email"]


def test_extraction_can_be_fetched_after_running(admin_client):
    record = _upload(admin_client, "figures.txt", TRIAL_BALANCE_TEXT)
    resp = admin_client.post(f"/files/{record['id']}/extract")
    assert resp.status_code == 200, resp.text

    resp = admin_client.get(f"/files/{record['id']}/extraction")
    assert resp.status_code == 200, resp.text
    assert resp.json()["labeled_figures"]["net_income"] == "234000"


def test_extraction_not_found_before_running(admin_client):
    record = _upload(admin_client, "untouched.txt", b"Total Revenue: $500")
    resp = admin_client.get(f"/files/{record['id']}/extraction")
    assert resp.status_code == 404


def test_unsupported_file_type_reports_status(admin_client):
    record = _upload(admin_client, "scan.pdf", b"%PDF-1.4 fake binary content", content_type="application/pdf")

    resp = admin_client.post(f"/files/{record['id']}/extract")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "unsupported_type"


def test_rerunning_extraction_replaces_previous_result(admin_client):
    record = _upload(admin_client, "figures.csv", b"Total Revenue: $100", content_type="text/csv")

    resp = admin_client.post(f"/files/{record['id']}/extract")
    first = resp.json()
    assert first["labeled_figures"]["total_revenue"] == "100"

    # Re-upload new content under the same file record isn't supported by
    # this API, so instead confirm re-running extraction on the same file
    # doesn't create a second row (idempotent replace, not accumulation).
    resp = admin_client.post(f"/files/{record['id']}/extract")
    second = resp.json()
    assert second["id"] == first["id"]


def test_extract_requires_existing_file(admin_client):
    resp = admin_client.post("/files/999999/extract")
    assert resp.status_code == 404

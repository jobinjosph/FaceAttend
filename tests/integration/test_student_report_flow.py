import pytest

from tests.component.test_student_report_routes import sample_report


def login(client):
    with client.session_transaction() as user_session:
        user_session.update(user_id=9, full_name="Test Student", role="STUDENT")


@pytest.mark.integration
def test_report_filters_are_passed_to_service(client, monkeypatch):
    login(client); captured = {}
    monkeypatch.setattr(
        "services.report_service.get_student_report",
        lambda user_id, filters: captured.update(user=user_id, filters=filters) or sample_report(),
    )
    response = client.get("/student/attendance?subject_id=1&month=2026-08&date=2026-08-20&semester_id=8")
    assert response.status_code == 200
    assert captured == {"user": 9, "filters": {"subject_id": 1, "month": "2026-08", "date": "2026-08-20", "semester_id": 8}}


@pytest.mark.integration
def test_csv_and_pdf_exports_use_filtered_student_report(client, monkeypatch):
    login(client)
    monkeypatch.setattr("services.report_service.get_student_report", lambda *args: sample_report())
    csv_response = client.get("/student/attendance/export.csv?subject_id=1")
    assert csv_response.status_code == 200
    assert csv_response.mimetype == "text/csv"
    assert b"CC431" in csv_response.data and b"47m 0s" in csv_response.data

    pdf_response = client.get("/student/attendance/export.pdf?subject_id=1")
    assert pdf_response.status_code == 200
    assert pdf_response.mimetype == "application/pdf"
    assert pdf_response.data.startswith(b"%PDF-1.4")


@pytest.mark.integration
def test_invalid_report_filter_returns_bad_request(client, monkeypatch):
    login(client)
    monkeypatch.setattr("services.report_service.get_student_report", lambda *args: sample_report())
    assert client.get("/student/attendance?month=2026-99").status_code == 400
    assert client.get("/student/attendance/export.csv?month=2026-99").status_code == 400

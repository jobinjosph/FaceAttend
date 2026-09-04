import pytest

from tests.component.test_attendance_report_routes import sample_cohort_report


@pytest.mark.integration
def test_filters_and_faculty_identity_reach_report_service(client, monkeypatch):
    captured = {}
    with client.session_transaction() as user_session:
        user_session.update(user_id=22, full_name="Dr. Faculty", role="FACULTY")

    def get_report(user_id, role, filters):
        captured.update(user_id=user_id, role=role, filters=filters)
        return sample_cohort_report({"id": 7, "full_name": "Dr. Faculty"})

    monkeypatch.setattr("services.report_service.get_cohort_report", get_report)
    response = client.get(
        "/reports/attendance?student_id=3&subject_id=4&month=2026-08&date=2026-08-25"
    )

    assert response.status_code == 200
    assert captured == {
        "user_id": 22, "role": "FACULTY",
        "filters": {"student_id": 3, "subject_id": 4, "month": "2026-08", "date": "2026-08-25", "semester_id": None},
    }


@pytest.mark.integration
def test_invalid_filter_prevents_export(client, monkeypatch):
    with client.session_transaction() as user_session:
        user_session.update(user_id=1, full_name="Admin", role="ADMIN")
    monkeypatch.setattr("services.report_service.get_cohort_report", lambda *args: sample_cohort_report())
    assert client.get("/reports/attendance/export.csv?student_id=wrong").status_code == 400

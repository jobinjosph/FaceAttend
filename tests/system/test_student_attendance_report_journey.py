import pytest

from tests.component.test_student_report_routes import sample_report


@pytest.mark.system
def test_student_opens_dashboard_views_report_and_exports_it(client, monkeypatch):
    monkeypatch.setattr("services.report_service.get_student_report", lambda *args: sample_report())
    with client.session_transaction() as user_session:
        user_session.update(user_id=9, full_name="Test Student", role="STUDENT")

    dashboard = client.get("/dashboard/student")
    assert dashboard.status_code == 200
    assert b"My Attendance" in dashboard.data

    report = client.get("/student/attendance")
    assert report.status_code == 200
    assert b"Semester View" in report.data
    assert b"Month View" in report.data
    assert b"Overall attendance" in report.data
    assert b"Cloud Computing" in report.data

    export = client.get("/student/attendance/export.csv")
    assert export.status_code == 200
    assert b"Test Student" in export.data

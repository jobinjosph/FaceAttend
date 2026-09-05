import pytest

from tests.component.test_attendance_report_routes import sample_cohort_report


@pytest.mark.system
@pytest.mark.parametrize(
    ("role", "dashboard_url", "module_text"),
    [("ADMIN", "/dashboard/admin", b"Attendance Reports"), ("FACULTY", "/dashboard/faculty", b"My Attendance Reports")],
)
def test_staff_opens_dashboard_views_filters_and_exports_report(
    client, monkeypatch, role, dashboard_url, module_text
):
    faculty = {"id": 7, "full_name": "Dr. Faculty"} if role == "FACULTY" else None
    monkeypatch.setattr("services.report_service.get_cohort_report", lambda *args: sample_cohort_report(faculty))
    if role == "ADMIN":
        monkeypatch.setattr(
            "services.academic_context_service.list_active_contexts",
            lambda: [{"id": 3, "course_code": "MCA", "course_name": "Master of Computer Applications", "semester_number": 3, "academic_year": "2026-27", "section": "A"}],
        )
    with client.session_transaction() as user_session:
        user_session.update(user_id=7, full_name="Report User", role=role)

    dashboard = client.get(dashboard_url)
    assert dashboard.status_code == 200 and module_text in dashboard.data

    report = client.get("/reports/attendance?subject_id=4&month=2026-08")
    assert report.status_code == 200
    assert b"Student attendance summary" in report.data
    assert b"Detailed attendance" in report.data
    assert b"Test Student" in report.data

    export = client.get("/reports/attendance/export.csv?subject_id=4&month=2026-08")
    assert export.status_code == 200 and b"Cloud Computing" in export.data

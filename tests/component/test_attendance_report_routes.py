from datetime import date, datetime

import pytest


def login(client, role):
    with client.session_transaction() as user_session:
        user_session.update(user_id=5, full_name="Report User", role=role)


def sample_cohort_report(faculty=None):
    return {
        "summary": {"percentage": 50.0, "total": 2, "attended": 1, "present": 1, "absent": 1, "late": 0, "left_early": 0, "on_duty": 0, "medical": 0},
        "students": [{"student_id": 3, "register_number": "25MCA03", "student_name": "Test Student", "percentage": 50.0, "attended": 1, "total": 2, "absent": 1, "low_attendance": True}],
        "history": [{"session_date": date(2026, 8, 25), "period_number": 1, "scheduled_start": "10:00", "scheduled_end": "10:50", "register_number": "25MCA03", "student_name": "Test Student", "subject_code": "CC431", "subject_name": "Cloud Computing", "faculty_name": "Dr. Faculty", "status": "PRESENT", "first_entry": datetime(2026, 8, 25, 10, 1), "last_exit": datetime(2026, 8, 25, 10, 48), "duration_label": "47m 0s", "marking_method": "FACE"}],
        "available_students": [{"id": 3, "register_number": "25MCA03", "full_name": "Test Student"}],
        "available_subjects": [{"id": 4, "subject_code": "CC431", "subject_name": "Cloud Computing"}],
        "faculty": faculty, "threshold": 75.0, "low_attendance_count": 1,
    }


def academic_contexts():
    return [
        {"id": 3, "course_code": "MCA", "course_name": "Master of Computer Applications", "semester_number": 3, "academic_year": "2026-27", "section": "A"},
        {"id": 22, "course_code": "BCA", "course_name": "Bachelor of Computer Applications", "semester_number": 2, "academic_year": "2026-27", "section": "A"},
    ]


def mock_academic_context(monkeypatch):
    contexts = academic_contexts()
    monkeypatch.setattr("services.academic_context_service.list_active_contexts", lambda: contexts)
    monkeypatch.setattr(
        "services.academic_context_service.get_active_context",
        lambda semester_id: next((item for item in contexts if item["id"] == semester_id), None),
    )


@pytest.mark.component
def test_attendance_report_requires_login(client):
    assert client.get("/reports/attendance").status_code == 302


@pytest.mark.component
def test_student_cannot_open_staff_report(client):
    login(client, "STUDENT")
    assert client.get("/reports/attendance").status_code == 403


@pytest.mark.component
@pytest.mark.parametrize("role", ["ADMIN", "FACULTY"])
def test_staff_report_displays_filters_shortage_and_history(client, monkeypatch, role):
    login(client, role)
    faculty = {"id": 7, "full_name": "Dr. Faculty"} if role == "FACULTY" else None
    monkeypatch.setattr("services.report_service.get_cohort_report", lambda *args: sample_cohort_report(faculty))
    if role == "ADMIN":
        mock_academic_context(monkeypatch)

    response = client.get("/reports/attendance")

    assert response.status_code == 200
    assert b'class="apple-shop-button"' in response.data
    assert b'class="apple-shop-button apple-shop-button-grey"' in response.data
    assert b'>Clear</a>' in response.data
    assert b"Attendance Reports" in response.data
    assert b"All students" in response.data and b"All subjects" in response.data
    assert b"All months" in response.data and b"January" in response.data and b"December" in response.data
    assert b"Below 75%" in response.data
    assert b"47m 0s" in response.data


@pytest.mark.component
def test_unlinked_faculty_receives_helpful_report_message(client, monkeypatch):
    login(client, "FACULTY")
    monkeypatch.setattr("services.report_service.get_cohort_report", lambda *args: None)
    response = client.get("/reports/attendance")
    assert response.status_code == 404
    assert b"Faculty profile is not linked" in response.data


@pytest.mark.component
def test_report_exports_csv_and_pdf(client, monkeypatch):
    login(client, "ADMIN")
    mock_academic_context(monkeypatch)
    monkeypatch.setattr("services.report_service.get_cohort_report", lambda *args: sample_cohort_report())
    csv_response = client.get("/reports/attendance/export.csv")
    pdf_response = client.get("/reports/attendance/export.pdf")
    assert csv_response.status_code == 200 and b"25MCA03" in csv_response.data
    assert pdf_response.status_code == 200 and pdf_response.data.startswith(b"%PDF-1.4")


@pytest.mark.component
def test_admin_report_filters_selected_non_mca_semester(client, monkeypatch):
    login(client, "ADMIN")
    mock_academic_context(monkeypatch)
    captured = {}
    monkeypatch.setattr(
        "services.report_service.get_cohort_report",
        lambda user_id, role, filters: captured.update(filters=filters) or sample_cohort_report(),
    )

    response = client.get("/reports/attendance?programme=BCA&semester=2")

    assert response.status_code == 200
    assert captured["filters"]["semester_id"] == 22
    assert b"BCA \xe2\x80\x94 Bachelor of Computer Applications" in response.data
    assert b'name="semester_id" value="22"' in response.data
    assert b"semester_id=22" in response.data


@pytest.mark.component
def test_invalid_admin_report_semester_returns_404(client, monkeypatch):
    login(client, "ADMIN")
    mock_academic_context(monkeypatch)

    assert client.get("/reports/attendance?semester_id=999").status_code == 404
    assert client.get("/reports/attendance/export.csv?semester_id=999").status_code == 404


@pytest.mark.component
@pytest.mark.parametrize("year,section,expected", [("2026-27", "A", 41), ("2026-27", "C", 42), ("2027-28", "C", 43)])
def test_report_selector_separates_years_and_sections(client, monkeypatch, year, section, expected):
    login(client, "ADMIN")
    contexts = [dict(id=identifier, course_code="NEW", course_name="New Programme",
                     semester_number=6, academic_year=academic_year, section=group)
                for identifier, academic_year, group in [(41, "2026-27", "A"), (42, "2026-27", "C"), (43, "2027-28", "C")]]
    monkeypatch.setattr("services.academic_context_service.list_active_contexts", lambda: contexts)
    captured = []
    monkeypatch.setattr(
        "services.report_service.get_cohort_report",
        lambda user_id, role, filters: captured.append(filters["semester_id"]) or sample_cohort_report(),
    )

    response = client.get(f"/reports/attendance?programme=NEW&academic_year={year}&semester=6&section={section}")

    assert response.status_code == 200
    assert captured == [expected]
    for field in ["programme", "academic_year", "semester", "section"]:
        assert f'name="{field}"'.encode() in response.data
    assert f'name="semester_id" value="{expected}"'.encode() in response.data
    assert f"semester_id={expected}".encode() in response.data


@pytest.mark.component
def test_admin_exports_are_scoped_to_selected_group(client, monkeypatch):
    login(client, "ADMIN")
    mock_academic_context(monkeypatch)
    captured = []
    monkeypatch.setattr(
        "services.report_service.get_cohort_report",
        lambda user_id, role, filters: captured.append(filters["semester_id"]) or sample_cohort_report(),
    )

    assert client.get("/reports/attendance/export.csv?semester_id=22").status_code == 200
    assert client.get("/reports/attendance/export.pdf?semester_id=22").status_code == 200
    assert captured == [22, 22]


@pytest.mark.component
def test_no_groups_does_not_load_or_export_college_wide_data(client, monkeypatch):
    login(client, "ADMIN")
    monkeypatch.setattr("services.academic_context_service.list_active_contexts", lambda: [])
    def unexpected(*args):
        pytest.fail("No group must not load an unscoped admin report")
    monkeypatch.setattr("services.report_service.get_cohort_report", unexpected)

    response = client.get("/reports/attendance")

    assert response.status_code == 200
    assert b"No active semester groups" in response.data
    assert b"No confirmed attendance found" in response.data
    assert client.get("/reports/attendance/export.csv").status_code == 404
    assert client.get("/reports/attendance/export.pdf").status_code == 404

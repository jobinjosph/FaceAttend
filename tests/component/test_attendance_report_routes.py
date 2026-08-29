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

    response = client.get("/reports/attendance")

    assert response.status_code == 200
    assert b'class="apple-shop-button"' in response.data
    assert b'class="apple-shop-button apple-shop-button-grey"' in response.data
    assert b"Attendance Reports" in response.data
    assert b"All students" in response.data and b"All subjects" in response.data
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
    monkeypatch.setattr("services.report_service.get_cohort_report", lambda *args: sample_cohort_report())
    csv_response = client.get("/reports/attendance/export.csv")
    pdf_response = client.get("/reports/attendance/export.pdf")
    assert csv_response.status_code == 200 and b"25MCA03" in csv_response.data
    assert pdf_response.status_code == 200 and pdf_response.data.startswith(b"%PDF-1.4")

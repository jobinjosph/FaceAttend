from datetime import date, datetime

import pytest


def login(client, role="STUDENT"):
    with client.session_transaction() as user_session:
        user_session.update(user_id=9, full_name="Test Student", role=role)


def sample_report():
    return {
        "student": {"id": 3, "register_number": "25MCA03", "full_name": "Test Student", "course_code": "MCA", "semester_number": 3},
        "summary": {"percentage": 50.0, "total": 2, "attended": 1, "present": 1, "absent": 1, "late": 0, "left_early": 0, "on_duty": 0, "medical": 0},
        "subjects": [{"subject_id": 1, "subject_code": "CC431", "subject_name": "Cloud Computing", "percentage": 50.0, "attended": 1, "total": 2, "low_attendance": True}],
        "history": [{"session_date": date(2026, 8, 20), "period_number": 1, "scheduled_start": "10:00", "scheduled_end": "10:50", "subject_code": "CC431", "subject_name": "Cloud Computing", "faculty_name": "Dr. Faculty", "status": "PRESENT", "first_entry": datetime(2026, 8, 20, 10, 1), "last_exit": datetime(2026, 8, 20, 10, 48), "duration_label": "47m 0s", "marking_method": "FACE"}],
        "available_subjects": [{"id": 1, "subject_code": "CC431", "subject_name": "Cloud Computing"}],
        "threshold": 75.0, "low_attendance": True,
    }


@pytest.mark.component
def test_student_report_requires_login(client):
    assert client.get("/student/attendance").status_code == 302


@pytest.mark.component
@pytest.mark.parametrize("role", ["ADMIN", "FACULTY"])
def test_non_students_cannot_open_student_report(client, role):
    login(client, role)
    assert client.get("/student/attendance").status_code == 403


@pytest.mark.component
def test_student_report_displays_summary_warning_and_history(client, monkeypatch):
    login(client)
    monkeypatch.setattr("services.report_service.get_student_report", lambda *args: sample_report())
    response = client.get("/student/attendance")
    assert response.status_code == 200
    assert b'class="apple-shop-button"' in response.data
    assert b'class="apple-shop-button apple-shop-button-grey"' in response.data
    assert b"50.0%" in response.data
    assert b"Attendance warning" in response.data
    assert b"Cloud Computing" in response.data
    assert b"47m 0s" in response.data
    assert b"Export CSV" in response.data and b"Export PDF" in response.data


@pytest.mark.component
def test_unlinked_student_gets_helpful_message(client, monkeypatch):
    login(client)
    monkeypatch.setattr("services.report_service.get_student_report", lambda *args: None)
    response = client.get("/student/attendance")
    assert response.status_code == 404
    assert b"Student profile is not linked" in response.data

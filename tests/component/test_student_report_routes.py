from datetime import date, datetime

import pytest


def login(client, role="STUDENT"):
    with client.session_transaction() as user_session:
        user_session.update(user_id=9, full_name="Test Student", role=role)


def sample_report():
    history = [{"session_date": date(2026, 8, 20), "period_number": 1, "scheduled_start": "10:00", "scheduled_end": "10:50", "subject_code": "CC431", "subject_name": "Cloud Computing", "faculty_name": "Dr. Faculty", "status": "PRESENT", "first_entry": datetime(2026, 8, 20, 10, 1), "last_exit": datetime(2026, 8, 20, 10, 48), "duration_label": "47m 0s", "marking_method": "FACE"}]
    return {
        "student": {"id": 3, "register_number": "25MCA03", "full_name": "Test Student", "course_code": "MCA", "semester_id": 8, "semester_number": 3, "academic_year": "2026-27", "section": "A"},
        "summary": {"percentage": 50.0, "total": 2, "attended": 1, "present": 1, "absent": 1, "late": 0, "left_early": 0, "on_duty": 0, "medical": 0},
        "subjects": [{"subject_id": 1, "subject_code": "CC431", "subject_name": "Cloud Computing", "percentage": 50.0, "attended": 1, "total": 2, "low_attendance": True}],
        "history": history,
        "months": [{"value": "2026-08", "year": 2026, "name": "August", "percentage": 50.0, "total": 2, "attended": 1, "absent": 1, "on_duty": 0, "medical": 0, "subjects": [{"subject_name": "Cloud Computing", "percentage": 50.0}]}],
        "dates": [{"value": "2026-08-20", "label": "20 August 2026", "rows": history}],
        "available_subjects": [{"id": 1, "subject_code": "CC431", "subject_name": "Cloud Computing"}],
        "available_placements": [
            {"id": 4, "course_code": "MCA", "academic_year": "2025-26", "semester_number": 2, "section": "A"},
            {"id": 8, "course_code": "MCA", "academic_year": "2026-27", "semester_number": 3, "section": "A"},
        ],
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
    assert b'>Clear</a>' in response.data
    assert b"50.0%" in response.data
    assert b"Attendance warning" in response.data
    assert b"Cloud Computing" in response.data
    assert b"Semester View" in response.data and b"Month View" in response.data and b"Date View" in response.data
    assert b"2025-26" in response.data and b"Semester 2" in response.data
    assert b"Semester 1" not in response.data and b"Semester 4" not in response.data
    month_response = client.get("/student/attendance?view=month")
    assert b"All months" in month_response.data and b"January" in month_response.data and b"December" in month_response.data
    assert b"August" in month_response.data
    date_response = client.get("/student/attendance?view=date")
    assert b"20 August 2026" in date_response.data and b"10:00" in date_response.data
    assert b"Export CSV" in response.data and b"Export PDF" in response.data


@pytest.mark.component
def test_unlinked_student_gets_helpful_message(client, monkeypatch):
    login(client)
    monkeypatch.setattr("services.report_service.get_student_report", lambda *args: None)
    response = client.get("/student/attendance")
    assert response.status_code == 404
    assert b"Student profile is not linked" in response.data


@pytest.mark.component
def test_student_cannot_open_an_unrecorded_placement(client, monkeypatch):
    login(client)
    report = sample_report()
    report["invalid_placement"] = True
    monkeypatch.setattr("services.report_service.get_student_report", lambda *args: report)

    response = client.get("/student/attendance?semester_id=999")

    assert response.status_code == 400
    assert b"do not have attendance access" in response.data

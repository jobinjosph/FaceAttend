from datetime import date, datetime

import pytest


def login(client, role):
    with client.session_transaction() as user_session:
        user_session.update(user_id=9, full_name="Test User", role=role)


def record():
    return {"attendance_record_id": 8, "current_status": "ABSENT", "session_date": date(2026, 8, 25), "period_number": 1, "scheduled_start": "10:00", "scheduled_end": "10:50", "subject_code": "CC431", "subject_name": "Cloud Computing", "faculty_name": "Dr. Faculty", "request_id": None, "request_status": None}


def request_item(status="PENDING"):
    return {"id": 4, "requested_status": "PRESENT", "reason": "Face failed", "status": status, "reviewer_comment": None, "reviewed_at": None, "created_at": datetime(2026, 8, 25, 12), "current_status": "ABSENT", "session_date": date(2026, 8, 25), "period_number": 1, "subject_code": "CC431", "subject_name": "Cloud Computing", "register_number": "25MCA03", "student_name": "Test Student", "faculty_name": "Dr. Faculty", "reviewer_name": None}


@pytest.mark.component
def test_student_correction_page_requires_login(client):
    assert client.get("/student/corrections").status_code == 302


@pytest.mark.component
def test_only_students_can_open_student_corrections(client):
    login(client, "FACULTY")
    assert client.get("/student/corrections").status_code == 403


@pytest.mark.component
def test_student_sees_request_form_and_history(client, monkeypatch):
    login(client, "STUDENT")
    monkeypatch.setattr("services.correction_service.list_student_records", lambda uid: [record()])
    monkeypatch.setattr("services.correction_service.list_student_requests", lambda uid: [request_item()])
    response = client.get("/student/corrections")
    assert response.status_code == 200
    assert b"Cloud Computing" in response.data
    assert b"Submit correction request" in response.data
    assert b"Face failed" in response.data


@pytest.mark.component
def test_students_cannot_open_staff_review_page(client):
    login(client, "STUDENT")
    assert client.get("/corrections").status_code == 403


@pytest.mark.component
@pytest.mark.parametrize("role", ["ADMIN", "FACULTY"])
def test_staff_can_view_pending_correction_requests(client, monkeypatch, role):
    login(client, role)
    monkeypatch.setattr("services.correction_service.list_review_requests", lambda *args: [request_item()])
    response = client.get("/corrections")
    assert response.status_code == 200
    assert b"Test Student" in response.data
    assert b"Approve correction" in response.data
    assert b"Reject" in response.data


@pytest.mark.component
def test_rejection_without_comment_is_refused(client, monkeypatch):
    login(client, "FACULTY")
    called = []
    monkeypatch.setattr("services.correction_service.review_request", lambda *args: called.append(args))
    response = client.post("/corrections/4/review", data={"decision": "REJECT", "comment": ""})
    assert response.status_code == 302
    assert called == []

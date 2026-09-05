from datetime import date, datetime

import pytest


@pytest.fixture(autouse=True)
def academic_context(monkeypatch):
    context = {"id": 3, "course_code": "MCA", "course_name": "Master of Computer Applications",
               "semester_number": 3, "section": "A", "academic_year": "2026-27"}
    monkeypatch.setattr("services.academic_context_service.list_active_contexts", lambda: [context])
    monkeypatch.setattr("services.academic_context_service.get_active_context",
                        lambda semester_id: context if semester_id == 3 else None)


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


@pytest.mark.component
@pytest.mark.parametrize("year,section,expected", [("2026-27", "A", 41), ("2026-27", "C", 42), ("2027-28", "C", 43)])
def test_correction_selector_separates_years_and_sections(client, monkeypatch, year, section, expected):
    login(client, "ADMIN")
    contexts = [dict(id=identifier, course_code="NEW", course_name="New Programme",
                     semester_number=6, academic_year=academic_year, section=group)
                for identifier, academic_year, group in [(41, "2026-27", "A"), (42, "2026-27", "C"), (43, "2027-28", "C")]]
    monkeypatch.setattr("services.academic_context_service.list_active_contexts", lambda: contexts)
    captured = []
    monkeypatch.setattr(
        "services.correction_service.list_review_requests",
        lambda user_id, role, status, semester_id: captured.append(semester_id) or [request_item()],
    )

    response = client.get(f"/corrections?status=PENDING&programme=NEW&academic_year={year}&semester=6&section={section}")

    assert response.status_code == 200
    assert captured == [expected]
    for field in ["programme", "academic_year", "semester", "section"]:
        assert f'name="{field}"'.encode() in response.data
    assert b'name="status" value="PENDING"' in response.data
    assert f'name="semester_id" value="{expected}"'.encode() in response.data


@pytest.mark.component
def test_admin_review_is_bound_to_selected_group(client, monkeypatch):
    login(client, "ADMIN")
    captured = {}
    monkeypatch.setattr(
        "services.correction_service.review_request",
        lambda request_id, user_id, role, data, semester_id: captured.update(
            request_id=request_id, semester_id=semester_id
        ) or "approved",
    )

    response = client.post(
        "/corrections/4/review",
        data={"semester_id": "3", "status": "PENDING", "decision": "APPROVE", "comment": "Verified"},
    )

    assert response.status_code == 302
    assert captured == {"request_id": 4, "semester_id": 3}
    assert "semester_id=3" in response.headers["Location"]


@pytest.mark.component
def test_no_groups_does_not_load_unscoped_admin_requests(client, monkeypatch):
    login(client, "ADMIN")
    monkeypatch.setattr("services.academic_context_service.list_active_contexts", lambda: [])
    monkeypatch.setattr(
        "services.correction_service.list_review_requests",
        lambda *args: pytest.fail("No group must not load unscoped requests"),
    )

    response = client.get("/corrections")

    assert response.status_code == 200
    assert b"No active semester groups" in response.data
    assert b"No pending requests" in response.data

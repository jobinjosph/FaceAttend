import pytest


def login(client, role, user_id=9):
    with client.session_transaction() as user_session:
        user_session.update(user_id=user_id, full_name="Test User", role=role)


@pytest.mark.integration
def test_valid_student_request_reaches_service(client, monkeypatch):
    login(client, "STUDENT")
    captured = {}
    monkeypatch.setattr("services.correction_service.create_request", lambda uid, data: captured.update(user_id=uid, data=data) or "created")
    monkeypatch.setattr("services.correction_service.list_student_records", lambda uid: [])
    monkeypatch.setattr("services.correction_service.list_student_requests", lambda uid: [])

    response = client.post("/student/corrections", data={"attendance_record_id": "8", "requested_status": "present", "reason": " Face failed "})

    assert response.status_code == 302
    assert captured == {"user_id": 9, "data": {"attendance_record_id": 8, "requested_status": "PRESENT", "reason": "Face failed"}}


@pytest.mark.integration
def test_faculty_identity_and_decision_reach_review_service(client, monkeypatch):
    login(client, "FACULTY", 22)
    captured = {}
    monkeypatch.setattr("services.correction_service.review_request", lambda request_id, uid, role, data: captured.update(request_id=request_id, user_id=uid, role=role, data=data) or "approved")

    response = client.post("/corrections/4/review", data={"decision": "APPROVE", "comment": "Verified"})

    assert response.status_code == 302
    assert captured == {"request_id": 4, "user_id": 22, "role": "FACULTY", "data": {"decision": "APPROVE", "comment": "Verified"}}


@pytest.mark.integration
def test_service_forbidden_result_becomes_http_403(client, monkeypatch):
    login(client, "FACULTY", 99)
    monkeypatch.setattr("services.correction_service.review_request", lambda *args: "forbidden")
    assert client.post("/corrections/4/review", data={"decision": "APPROVE", "comment": ""}).status_code == 403

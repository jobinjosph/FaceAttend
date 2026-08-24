from datetime import date, datetime

import pytest

from tests.component.test_correction_routes import record, request_item


@pytest.mark.system
def test_student_submits_and_faculty_approves_correction(client, monkeypatch):
    requests = []

    def create_request(user_id, data):
        item = request_item()
        item.update(id=4, requested_status=data["requested_status"], reason=data["reason"])
        requests.append(item)
        return "created"

    def review_request(request_id, user_id, role, data):
        requests[0].update(status="APPROVED", current_status="PRESENT", reviewer_comment=data["comment"], reviewer_name="Dr. Faculty", reviewed_at=datetime(2026, 8, 25, 13))
        return "approved"

    monkeypatch.setattr("services.correction_service.create_request", create_request)
    monkeypatch.setattr("services.correction_service.list_student_records", lambda uid: [record()])
    monkeypatch.setattr("services.correction_service.list_student_requests", lambda uid: requests)
    monkeypatch.setattr("services.correction_service.list_review_requests", lambda uid, role, status: [item for item in requests if item["status"] == status])
    monkeypatch.setattr("services.correction_service.review_request", review_request)

    with client.session_transaction() as user_session:
        user_session.update(user_id=9, full_name="Test Student", role="STUDENT")
    dashboard = client.get("/dashboard/student")
    assert b"Attendance Corrections" in dashboard.data
    submitted = client.post("/student/corrections", data={"attendance_record_id": "8", "requested_status": "PRESENT", "reason": "Face recognition failed"}, follow_redirects=True)
    assert submitted.status_code == 200 and b"Pending" in submitted.data

    with client.session_transaction() as user_session:
        user_session.clear()
        user_session.update(user_id=22, full_name="Dr. Faculty", role="FACULTY")
    review_page = client.get("/corrections")
    assert review_page.status_code == 200 and b"Face recognition failed" in review_page.data
    approved = client.post("/corrections/4/review", data={"decision": "APPROVE", "comment": "Verified in class"}, follow_redirects=True)
    assert approved.status_code == 200 and b"attendance updated" in approved.data

    with client.session_transaction() as user_session:
        user_session.clear()
        user_session.update(user_id=9, full_name="Test Student", role="STUDENT")
    history = client.get("/student/corrections")
    assert b"Approved" in history.data and b"Verified in class" in history.data

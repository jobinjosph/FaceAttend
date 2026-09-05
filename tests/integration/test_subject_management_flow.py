import mysql.connector
import pytest


def login_admin(client):
    with client.session_transaction() as user_session:
        user_session.update(user_id=1, full_name="Admin", role="ADMIN")


@pytest.fixture(autouse=True)
def mock_academic_context(monkeypatch):
    context = {
        "id": 3, "course_id": 1, "course_code": "MCA",
        "course_name": "Master of Computer Applications", "academic_year": "2026-27",
        "semester_number": 3, "section": "A",
    }
    monkeypatch.setattr("services.academic_context_service.list_active_contexts", lambda: [context])
    monkeypatch.setattr("services.academic_context_service.get_active_context", lambda semester_id: context)


@pytest.mark.integration
def test_valid_subject_is_attached_to_selected_academic_group(client, monkeypatch):
    login_admin(client)
    captured = {}
    monkeypatch.setattr("services.subject_service.create_subject", lambda data, semester_id: captured.update(data=data, semester_id=semester_id) or 1)
    response = client.post("/admin/subjects/add", data={
        "subject_code": "ai433", "subject_name": "Artificial Intelligence",
        "activity_type": "THEORY",
    })
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/subjects?semester_id=3")
    assert captured["semester_id"] == 3
    assert captured["data"]["subject_code"] == "AI433"


@pytest.mark.integration
def test_duplicate_subject_code_is_rejected(client, monkeypatch):
    login_admin(client)
    def duplicate(data, semester_id):
        raise mysql.connector.IntegrityError("duplicate")
    monkeypatch.setattr("services.subject_service.create_subject", duplicate)
    response = client.post("/admin/subjects/add", data={
        "subject_code": "CC431", "subject_name": "Cloud Computing",
        "activity_type": "LECTURE",
    })
    assert response.status_code == 409
    assert b"subject code is already in use" in response.data

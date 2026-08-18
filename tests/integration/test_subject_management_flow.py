import mysql.connector
import pytest


def login_admin(client):
    with client.session_transaction() as user_session:
        user_session.update(user_id=1, full_name="Admin", role="ADMIN")


@pytest.mark.integration
def test_valid_subject_is_attached_to_mca_semester_three(client, monkeypatch):
    login_admin(client)
    captured = {}
    monkeypatch.setattr("services.subject_service.get_mca_semester_three", lambda: {"id": 3})
    monkeypatch.setattr("services.subject_service.create_subject", lambda data, semester_id: captured.update(data=data, semester_id=semester_id) or 1)
    response = client.post("/admin/subjects/add", data={
        "subject_code": "ai433", "subject_name": "Artificial Intelligence",
        "activity_type": "THEORY",
    })
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/subjects")
    assert captured["semester_id"] == 3
    assert captured["data"]["subject_code"] == "AI433"


@pytest.mark.integration
def test_duplicate_subject_code_is_rejected(client, monkeypatch):
    login_admin(client)
    monkeypatch.setattr("services.subject_service.get_mca_semester_three", lambda: {"id": 3})
    def duplicate(data, semester_id):
        raise mysql.connector.IntegrityError("duplicate")
    monkeypatch.setattr("services.subject_service.create_subject", duplicate)
    response = client.post("/admin/subjects/add", data={
        "subject_code": "CC431", "subject_name": "Cloud Computing",
        "activity_type": "LECTURE",
    })
    assert response.status_code == 409
    assert b"subject code is already in use" in response.data

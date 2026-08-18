import mysql.connector
import pytest


def login_admin(client):
    with client.session_transaction() as user_session:
        user_session["user_id"] = 1
        user_session["full_name"] = "Admin"
        user_session["role"] = "ADMIN"


def form_data(**changes):
    data = {
        "employee_code": "fc 001",
        "full_name": "Test Faculty",
        "email": "faculty@example.com",
        "password": "FacultyPass123",
    }
    data.update(changes)
    return data


@pytest.mark.integration
def test_valid_faculty_creates_linked_account_and_redirects(client, monkeypatch):
    login_admin(client)
    captured = {}
    monkeypatch.setattr(
        "services.faculty_service.create_faculty",
        lambda data: captured.update(data) or 4,
    )

    response = client.post("/admin/faculty/add", data=form_data())

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/faculty")
    assert captured["employee_code"] == "FC001"
    assert captured["email"] == "faculty@example.com"


@pytest.mark.integration
def test_duplicate_faculty_email_or_code_is_rejected(client, monkeypatch):
    login_admin(client)

    def duplicate(data):
        raise mysql.connector.IntegrityError("duplicate")

    monkeypatch.setattr("services.faculty_service.create_faculty", duplicate)

    response = client.post("/admin/faculty/add", data=form_data())

    assert response.status_code == 409
    assert b"Employee code or email is already in use" in response.data


@pytest.mark.integration
def test_faculty_edit_can_keep_current_password(client, monkeypatch):
    login_admin(client)
    existing = {
        "id": 5,
        "user_id": 8,
        "employee_code": "FC001",
        "full_name": "Test Faculty",
        "email": "faculty@example.com",
        "is_active": True,
    }
    captured = {}
    monkeypatch.setattr("services.faculty_service.get_faculty", lambda faculty_id: existing)
    monkeypatch.setattr(
        "services.faculty_service.update_faculty",
        lambda faculty_id, data: captured.update(data) or True,
    )

    response = client.post(
        "/admin/faculty/5/edit",
        data=form_data(full_name="Updated Faculty", password=""),
    )

    assert response.status_code == 302
    assert captured["full_name"] == "Updated Faculty"
    assert captured["password"] == ""


@pytest.mark.integration
def test_faculty_password_reset_requires_eight_characters(client, monkeypatch):
    login_admin(client)
    monkeypatch.setattr(
        "services.faculty_service.get_faculty",
        lambda faculty_id: {"id": faculty_id, "user_id": 8},
    )

    response = client.post(
        "/admin/faculty/5/edit",
        data=form_data(password="short"),
    )

    assert response.status_code == 400
    assert b"Password must contain at least 8 characters" in response.data


@pytest.mark.integration
def test_deactivating_faculty_calls_linked_account_service(client, monkeypatch):
    login_admin(client)
    captured = {}
    monkeypatch.setattr(
        "services.faculty_service.get_faculty",
        lambda faculty_id: {"id": faculty_id, "user_id": 8, "is_active": True},
    )
    monkeypatch.setattr(
        "services.faculty_service.set_faculty_active",
        lambda faculty_id, active: captured.update(id=faculty_id, active=active),
    )

    response = client.post("/admin/faculty/5/status", data={"is_active": "0"})

    assert response.status_code == 302
    assert captured == {"id": 5, "active": False}

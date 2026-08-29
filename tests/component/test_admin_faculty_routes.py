import mysql.connector
import pytest


def login_as(client, role):
    with client.session_transaction() as user_session:
        user_session["user_id"] = 1
        user_session["full_name"] = "Role User"
        user_session["role"] = role


@pytest.mark.component
def test_faculty_list_requires_login(client):
    response = client.get("/admin/faculty")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


@pytest.mark.component
@pytest.mark.parametrize("role", ["FACULTY", "STUDENT"])
def test_non_admin_roles_cannot_manage_faculty(client, role):
    login_as(client, role)

    assert client.get("/admin/faculty").status_code == 403
    assert client.get("/admin/faculty/add").status_code == 403


@pytest.mark.component
def test_admin_can_open_empty_faculty_list(client, monkeypatch):
    login_as(client, "ADMIN")
    monkeypatch.setattr("services.faculty_service.list_faculty", lambda: [])

    response = client.get("/admin/faculty")

    assert response.status_code == 200
    assert b'<a class="apple-shop-button"' in response.data
    assert b"No faculty members added yet" in response.data


@pytest.mark.component
def test_admin_can_open_add_faculty_form(client):
    login_as(client, "ADMIN")

    response = client.get("/admin/faculty/add")

    assert response.status_code == 200
    assert b"Create faculty account" in response.data
    assert b"Initial password" in response.data


@pytest.mark.component
def test_invalid_faculty_form_displays_errors(client):
    login_as(client, "ADMIN")

    response = client.post("/admin/faculty/add", data={})

    assert response.status_code == 400
    assert b"Employee code is required." in response.data
    assert b"Faculty name is required." in response.data
    assert b"initial password is required" in response.data


@pytest.mark.component
def test_unknown_faculty_edit_returns_404(client, monkeypatch):
    login_as(client, "ADMIN")
    monkeypatch.setattr("services.faculty_service.get_faculty", lambda faculty_id: None)

    assert client.get("/admin/faculty/999/edit").status_code == 404


@pytest.mark.component
def test_faculty_list_database_error_is_controlled(client, monkeypatch):
    login_as(client, "ADMIN")

    def failure():
        raise mysql.connector.Error("private database detail")

    monkeypatch.setattr("services.faculty_service.list_faculty", failure)

    response = client.get("/admin/faculty")

    assert response.status_code == 200
    assert b"Faculty could not be loaded" in response.data
    assert b"private database detail" not in response.data

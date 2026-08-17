import pytest
import mysql.connector


def login_as(client, role):
    with client.session_transaction() as user_session:
        user_session["user_id"] = 1
        user_session["full_name"] = "Role User"
        user_session["role"] = role


def academic_options():
    return (
        [{"id": 1, "code": "MCA", "name": "Master of Computer Applications"}],
        [
            {
                "id": 2,
                "course_id": 1,
                "semester_number": 3,
                "section": "A",
                "academic_year": "2026-27",
            }
        ],
    )


@pytest.mark.component
def test_student_list_requires_login(client):
    response = client.get("/admin/students")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


@pytest.mark.component
@pytest.mark.parametrize("role", ["FACULTY", "STUDENT"])
def test_non_admin_roles_cannot_access_student_management(client, role):
    login_as(client, role)

    assert client.get("/admin/students").status_code == 403
    assert client.get("/admin/students/add").status_code == 403


@pytest.mark.component
def test_admin_can_open_empty_student_list(client, monkeypatch):
    login_as(client, "ADMIN")
    monkeypatch.setattr("services.student_service.list_students", lambda: [])

    response = client.get("/admin/students")

    assert response.status_code == 200
    assert b"No students added yet" in response.data


@pytest.mark.component
def test_admin_can_open_add_student_form(client, monkeypatch):
    login_as(client, "ADMIN")
    monkeypatch.setattr(
        "services.student_service.get_academic_options",
        academic_options,
    )

    response = client.get("/admin/students/add")

    assert response.status_code == 200
    assert b"Add student" in response.data
    assert b"Cloud" not in response.data
    assert b"MCA" in response.data
    assert b"Semester 3" in response.data
    assert b"Section A" not in response.data
    assert b"2026-27" not in response.data
    assert b"Search programmes" in response.data
    assert b'data-course-combobox' in response.data
    assert b'data-value="1"' in response.data


@pytest.mark.component
def test_invalid_student_form_displays_errors(client, monkeypatch):
    login_as(client, "ADMIN")
    monkeypatch.setattr(
        "services.student_service.get_academic_options",
        academic_options,
    )

    response = client.post("/admin/students/add", data={})

    assert response.status_code == 400
    assert b"Register number is required." in response.data
    assert b"Student name is required." in response.data


@pytest.mark.component
def test_unknown_student_edit_returns_404(client, monkeypatch):
    login_as(client, "ADMIN")
    monkeypatch.setattr("services.student_service.get_student", lambda student_id: None)

    response = client.get("/admin/students/999/edit")

    assert response.status_code == 404


@pytest.mark.component
def test_student_form_database_failure_is_controlled(client, monkeypatch):
    login_as(client, "ADMIN")

    def database_failure():
        raise mysql.connector.Error("private database detail")

    monkeypatch.setattr(
        "services.student_service.get_academic_options",
        database_failure,
    )

    response = client.get("/admin/students/add")

    assert response.status_code == 503
    assert b"Database unavailable" in response.data
    assert b"private database detail" not in response.data

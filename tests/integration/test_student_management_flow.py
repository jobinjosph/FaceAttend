import mysql.connector
import pytest


def login_admin(client):
    with client.session_transaction() as user_session:
        user_session["user_id"] = 1
        user_session["full_name"] = "Admin"
        user_session["role"] = "ADMIN"


def form_data(**changes):
    data = {
        "register_number": "23mca104",
        "full_name": "Test Student",
        "email": "student@example.com",
        "password": "Student@123",
        "course_id": "1",
        "semester_id": "2",
    }
    data.update(changes)
    return data


def contexts():
    return [
        {"id": 2, "course_id": 1, "course_code": "MCA", "course_name": "MCA",
         "semester_number": 3, "section": "A", "academic_year": "2026-27"},
        {"id": 3, "course_id": 1, "course_code": "MCA", "course_name": "MCA",
         "semester_number": 4, "section": "A", "academic_year": "2026-27"},
    ]


@pytest.mark.integration
def test_valid_student_is_sent_to_service_and_redirected(client, monkeypatch):
    login_admin(client)
    captured = {}
    monkeypatch.setattr("services.student_service.active_semester_belongs_to_course", lambda *args: True)
    monkeypatch.setattr(
        "services.student_service.create_student",
        lambda data: captured.update(data) or 5,
    )

    response = client.post("/admin/students/add", data=form_data())

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/students?semester_id=2")
    assert captured["register_number"] == "23MCA104"
    assert captured["course_id"] == 1
    assert captured["password"] == "Student@123"


@pytest.mark.integration
def test_student_creation_requires_an_initial_password(client, monkeypatch):
    login_admin(client)
    monkeypatch.setattr("services.academic_context_service.list_active_contexts", contexts)

    response = client.post("/admin/students/add", data=form_data(password=""))

    assert response.status_code == 400
    assert b"initial password is required" in response.data


@pytest.mark.integration
def test_duplicate_student_login_email_is_rejected(client, monkeypatch):
    login_admin(client)
    monkeypatch.setattr("services.student_service.active_semester_belongs_to_course", lambda *args: True)
    monkeypatch.setattr("services.academic_context_service.list_active_contexts", contexts)

    def duplicate_email(data):
        raise mysql.connector.IntegrityError("Duplicate entry for key users.email")

    monkeypatch.setattr("services.student_service.create_student", duplicate_email)

    response = client.post("/admin/students/add", data=form_data())

    assert response.status_code == 409
    assert b"email address is already used" in response.data


@pytest.mark.integration
def test_duplicate_register_number_is_rejected(client, monkeypatch):
    login_admin(client)
    monkeypatch.setattr("services.student_service.active_semester_belongs_to_course", lambda *args: True)
    monkeypatch.setattr("services.academic_context_service.list_active_contexts", contexts)

    def duplicate_student(data):
        raise mysql.connector.IntegrityError("duplicate")

    monkeypatch.setattr("services.student_service.create_student", duplicate_student)

    response = client.post("/admin/students/add", data=form_data())

    assert response.status_code == 409
    assert b"register number is already in use" in response.data


@pytest.mark.integration
def test_semester_must_belong_to_selected_course(client, monkeypatch):
    login_admin(client)
    monkeypatch.setattr("services.student_service.active_semester_belongs_to_course", lambda *args: False)
    monkeypatch.setattr("services.academic_context_service.list_active_contexts", contexts)

    response = client.post("/admin/students/add", data=form_data())

    assert response.status_code == 400
    assert b"semester belonging to this course" in response.data


@pytest.mark.integration
def test_student_can_be_deactivated(client, monkeypatch):
    login_admin(client)
    captured = {}
    monkeypatch.setattr(
        "services.student_service.get_student",
        lambda student_id: {"id": student_id, "is_active": True, "semester_id": 2},
    )
    monkeypatch.setattr(
        "services.student_service.set_student_lifecycle_status",
        lambda student_id, status, admin: captured.update(id=student_id, status=status, admin=admin),
    )

    response = client.post("/admin/students/8/status", data={"is_active": "0"})

    assert response.status_code == 302
    assert captured == {"id": 8, "status": "ARCHIVED", "admin": 1}


@pytest.mark.integration
def test_selected_students_are_moved_to_an_active_destination(client, monkeypatch):
    login_admin(client)
    captured = {}
    monkeypatch.setattr("services.academic_context_service.list_active_contexts", contexts)
    monkeypatch.setattr("services.student_service.list_students", lambda semester_id: [])
    monkeypatch.setattr(
        "services.student_service.move_students",
        lambda ids, source, destination, admin: captured.update(
            ids=ids, source=source, destination=destination, admin=admin
        ) or len(ids),
    )

    response = client.post(
        "/admin/students/placement",
        data={"semester_id": "2", "destination_semester_id": "3", "student_id": ["7", "8"]},
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/students?semester_id=3")
    assert captured == {"ids": [7, 8], "source": 2, "destination": 3, "admin": 1}


@pytest.mark.integration
def test_placement_rejects_same_group_and_empty_selection(client, monkeypatch):
    login_admin(client)
    monkeypatch.setattr("services.academic_context_service.list_active_contexts", contexts)
    monkeypatch.setattr("services.student_service.list_students", lambda semester_id: [])

    response = client.post(
        "/admin/students/placement",
        data={"semester_id": "2", "destination_semester_id": "2"},
    )

    assert response.status_code == 400
    assert b"Select at least one student" in response.data
    assert b"different from the current group" in response.data


@pytest.mark.integration
def test_admin_can_mark_student_as_graduated(client, monkeypatch):
    login_admin(client)
    captured = {}
    monkeypatch.setattr(
        "services.student_service.get_student",
        lambda student_id: {"id": student_id, "semester_id": 2},
    )
    monkeypatch.setattr(
        "services.student_service.set_student_lifecycle_status",
        lambda student_id, status, admin: captured.update(
            student_id=student_id, status=status, admin=admin
        ),
    )

    response = client.post(
        "/admin/students/8/lifecycle",
        data={"lifecycle_status": "GRADUATED", "return_status": "ACTIVE"},
    )

    assert response.status_code == 302
    assert captured == {"student_id": 8, "status": "GRADUATED", "admin": 1}
    assert "semester_id=2" in response.headers["Location"]

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
        "course_id": "1",
        "semester_id": "2",
    }
    data.update(changes)
    return data


def options():
    return ([{"id": 1, "code": "MCA", "name": "MCA"}], [])


@pytest.mark.integration
def test_valid_student_is_sent_to_service_and_redirected(client, monkeypatch):
    login_admin(client)
    captured = {}
    monkeypatch.setattr("services.student_service.semester_belongs_to_course", lambda *args: True)
    monkeypatch.setattr("services.student_service.get_academic_options", options)
    monkeypatch.setattr(
        "services.student_service.create_student",
        lambda data: captured.update(data) or 5,
    )

    response = client.post("/admin/students/add", data=form_data())

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/students")
    assert captured["register_number"] == "23MCA104"
    assert captured["course_id"] == 1


@pytest.mark.integration
def test_duplicate_register_number_is_rejected(client, monkeypatch):
    login_admin(client)
    monkeypatch.setattr("services.student_service.semester_belongs_to_course", lambda *args: True)
    monkeypatch.setattr("services.student_service.get_academic_options", options)

    def duplicate_student(data):
        raise mysql.connector.IntegrityError("duplicate")

    monkeypatch.setattr("services.student_service.create_student", duplicate_student)

    response = client.post("/admin/students/add", data=form_data())

    assert response.status_code == 409
    assert b"register number is already in use" in response.data


@pytest.mark.integration
def test_semester_must_belong_to_selected_course(client, monkeypatch):
    login_admin(client)
    monkeypatch.setattr("services.student_service.semester_belongs_to_course", lambda *args: False)
    monkeypatch.setattr("services.student_service.get_academic_options", options)

    response = client.post("/admin/students/add", data=form_data())

    assert response.status_code == 400
    assert b"semester belonging to this course" in response.data


@pytest.mark.integration
def test_student_can_be_deactivated(client, monkeypatch):
    login_admin(client)
    captured = {}
    monkeypatch.setattr(
        "services.student_service.get_student",
        lambda student_id: {"id": student_id, "is_active": True},
    )
    monkeypatch.setattr(
        "services.student_service.set_student_active",
        lambda student_id, active: captured.update(id=student_id, active=active),
    )

    response = client.post("/admin/students/8/status", data={"is_active": "0"})

    assert response.status_code == 302
    assert captured == {"id": 8, "active": False}

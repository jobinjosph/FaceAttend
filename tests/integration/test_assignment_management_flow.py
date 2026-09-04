import mysql.connector
import pytest


def login_admin(client):
    with client.session_transaction() as session:
        session.update(user_id=1, full_name="Admin", role="ADMIN")


def options():
    return ([{"id": 3, "subject_code": "CC431", "subject_name": "Cloud Computing"}], [{"id": 8, "employee_code": "FC01", "full_name": "Faculty"}])


@pytest.mark.integration
def test_admin_assigns_active_faculty_to_active_subject(client, monkeypatch):
    login_admin(client)
    captured = {}
    monkeypatch.setattr("services.assignment_service.active_subject_exists", lambda subject_id: True)
    monkeypatch.setattr("services.assignment_service.active_faculty_exists", lambda faculty_id: True)
    monkeypatch.setattr("services.assignment_service.create_assignment", lambda data: captured.update(data) or 1)
    response = client.post("/admin/faculty-subjects/add", data={"subject_id": "3", "faculty_id": "8"})
    assert response.status_code == 302
    assert captured == {"subject_id": 3, "faculty_id": 8}


@pytest.mark.integration
def test_inactive_subject_cannot_be_assigned(client, monkeypatch):
    login_admin(client)
    monkeypatch.setattr("services.assignment_service.active_subject_exists", lambda subject_id: False)
    monkeypatch.setattr("services.assignment_service.get_assignment_options", options)
    response = client.post("/admin/faculty-subjects/add", data={"subject_id": "3", "faculty_id": "8"})
    assert response.status_code == 400
    assert b"active subject from the selected programme and semester" in response.data


@pytest.mark.integration
def test_inactive_faculty_cannot_be_assigned(client, monkeypatch):
    login_admin(client)
    monkeypatch.setattr("services.assignment_service.active_subject_exists", lambda subject_id: True)
    monkeypatch.setattr("services.assignment_service.active_faculty_exists", lambda faculty_id: False)
    monkeypatch.setattr("services.assignment_service.get_assignment_options", options)
    response = client.post("/admin/faculty-subjects/add", data={"subject_id": "3", "faculty_id": "8"})
    assert response.status_code == 400
    assert b"active faculty member" in response.data


@pytest.mark.integration
def test_duplicate_assignment_is_rejected(client, monkeypatch):
    login_admin(client)
    monkeypatch.setattr("services.assignment_service.active_subject_exists", lambda subject_id: True)
    monkeypatch.setattr("services.assignment_service.active_faculty_exists", lambda faculty_id: True)
    monkeypatch.setattr("services.assignment_service.get_assignment_options", options)
    def duplicate(data):
        raise mysql.connector.IntegrityError("duplicate")
    monkeypatch.setattr("services.assignment_service.create_assignment", duplicate)
    response = client.post("/admin/faculty-subjects/add", data={"subject_id": "3", "faculty_id": "8"})
    assert response.status_code == 409
    assert b"already assigned" in response.data


@pytest.mark.integration
def test_admin_assigns_faculty_inside_selected_non_mca_semester(client, monkeypatch):
    login_admin(client)
    context = {
        "id": 22, "course_code": "BCA", "course_name": "Bachelor of Computer Applications",
        "semester_number": 2, "section": "A", "academic_year": "2026-27",
    }
    captured = {}
    monkeypatch.setattr("services.timetable_service.get_timetable_context", lambda semester_id: context)
    monkeypatch.setattr(
        "services.assignment_service.active_subject_exists",
        lambda subject_id, semester_id: (subject_id, semester_id) == (30, 22),
    )
    monkeypatch.setattr("services.assignment_service.active_faculty_exists", lambda faculty_id: True)
    monkeypatch.setattr("services.assignment_service.create_assignment", lambda data: captured.update(data) or 1)

    response = client.post(
        "/admin/faculty-subjects/add",
        data={"semester_id": "22", "subject_id": "30", "faculty_id": "8"},
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/faculty-subjects?semester_id=22")
    assert captured == {"subject_id": 30, "faculty_id": 8}


@pytest.mark.integration
def test_subject_from_another_semester_cannot_be_assigned(client, monkeypatch):
    login_admin(client)
    context = {
        "id": 22, "course_code": "BCA", "course_name": "Bachelor of Computer Applications",
        "semester_number": 2, "section": "A", "academic_year": "2026-27",
    }
    monkeypatch.setattr("services.timetable_service.get_timetable_context", lambda semester_id: context)
    monkeypatch.setattr("services.assignment_service.active_subject_exists", lambda subject_id, semester_id: False)
    monkeypatch.setattr("services.assignment_service.get_assignment_options", lambda semester_id: options())

    response = client.post(
        "/admin/faculty-subjects/add",
        data={"semester_id": "22", "subject_id": "3", "faculty_id": "8"},
    )

    assert response.status_code == 400
    assert b"active subject from the selected programme and semester" in response.data
    assert b"Admin \xc2\xb7 BCA Semester 2" in response.data

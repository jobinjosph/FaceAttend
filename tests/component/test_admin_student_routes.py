import pytest
import mysql.connector
from datetime import datetime
from io import BytesIO


def login_as(client, role):
    with client.session_transaction() as user_session:
        user_session["user_id"] = 1
        user_session["full_name"] = "Role User"
        user_session["role"] = role


def academic_contexts():
    return [{
        "id": 2, "course_id": 1, "course_code": "MCA",
        "course_name": "Master of Computer Applications", "semester_number": 3,
        "section": "A", "academic_year": "2026-27",
    }, {
        "id": 3, "course_id": 1, "course_code": "MCA",
        "course_name": "Master of Computer Applications", "semester_number": 4,
        "section": "A", "academic_year": "2026-27",
    }]


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
    monkeypatch.setattr("services.academic_context_service.list_active_contexts", academic_contexts)
    monkeypatch.setattr("services.student_service.list_students", lambda semester_id: [])

    response = client.get("/admin/students")

    assert response.status_code == 200
    assert b'<a class="apple-shop-button"' in response.data
    assert b"No students added yet" in response.data


@pytest.mark.component
def test_admin_can_open_add_student_form(client, monkeypatch):
    login_as(client, "ADMIN")
    monkeypatch.setattr(
        "services.academic_context_service.list_active_contexts",
        academic_contexts,
    )

    response = client.get("/admin/students/add")

    assert response.status_code == 200
    assert b"Add student" in response.data
    assert b"Cloud" not in response.data
    assert b"MCA" in response.data
    assert b"Semester 3" in response.data
    assert b"Section A" in response.data
    assert b"2026-27" in response.data
    assert b'name="course_id"' in response.data
    assert b'id="student_academic_year"' in response.data
    assert b"Student login email" in response.data
    assert b"Initial password" in response.data


@pytest.mark.component
def test_invalid_student_form_displays_errors(client, monkeypatch):
    login_as(client, "ADMIN")
    monkeypatch.setattr(
        "services.academic_context_service.list_active_contexts",
        academic_contexts,
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
        "services.academic_context_service.list_active_contexts",
        database_failure,
    )

    response = client.get("/admin/students/add")

    assert response.status_code == 503
    assert b"Database unavailable" in response.data
    assert b"private database detail" not in response.data


@pytest.mark.component
def test_admin_can_open_student_placement_page(client, monkeypatch):
    login_as(client, "ADMIN")
    monkeypatch.setattr("services.academic_context_service.list_active_contexts", academic_contexts)
    monkeypatch.setattr(
        "services.student_service.list_students",
        lambda semester_id: [{"id": 8, "register_number": "23MCA08", "full_name": "Student",
                              "email": "student@example.com", "is_active": True}],
    )

    response = client.get("/admin/students/placement?semester_id=2")

    assert response.status_code == 200
    assert b"Promote or transfer students" in response.data
    assert b"MCA" in response.data
    assert b"Semester 4" in response.data
    assert b' name="student_id" value="8"' in response.data


@pytest.mark.component
def test_admin_can_view_student_placement_history(client, monkeypatch):
    login_as(client, "ADMIN")
    monkeypatch.setattr(
        "services.student_service.get_student",
        lambda student_id: {"id": student_id, "register_number": "23MCA08",
                            "full_name": "Test Student", "semester_id": 3},
    )
    monkeypatch.setattr(
        "services.student_service.get_placement_history",
        lambda student_id: [{
            "moved_at": datetime(2026, 9, 6, 10, 30),
            "from_course_code": "MCA", "from_course_name": "Master of Computer Applications",
            "from_academic_year": "2026-27", "from_semester_number": 3, "from_section": "A",
            "to_course_code": "MCA", "to_course_name": "Master of Computer Applications",
            "to_academic_year": "2026-27", "to_semester_number": 4, "to_section": "B",
            "moved_by_name": "Admin",
        }],
    )

    response = client.get("/admin/students/8/placement-history")

    assert response.status_code == 200
    assert b"Placement history" in response.data
    assert b"Semester 3" in response.data
    assert b"Section B" in response.data
    assert b"Admin" in response.data


@pytest.mark.component
def test_unknown_student_placement_history_returns_404(client, monkeypatch):
    login_as(client, "ADMIN")
    monkeypatch.setattr("services.student_service.get_student", lambda student_id: None)

    assert client.get("/admin/students/999/placement-history").status_code == 404


@pytest.mark.component
def test_admin_can_download_bulk_enrolment_template(client):
    login_as(client, "ADMIN")

    response = client.get("/admin/students/import/template.csv")

    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert b"register_number,full_name,email,initial_password" in response.data


@pytest.mark.component
def test_admin_can_import_valid_student_csv(client, monkeypatch):
    login_as(client, "ADMIN")
    context = academic_contexts()[0]
    captured = {}
    monkeypatch.setattr("services.academic_context_service.get_active_context", lambda semester_id: context)
    monkeypatch.setattr(
        "services.student_service.bulk_create_students",
        lambda rows: captured.update(rows=rows) or len(rows),
    )
    csv_data = (
        b"register_number,full_name,email,initial_password\n"
        b"25mca001,Test Student,STUDENT@example.com,Student123\n"
    )

    response = client.post(
        "/admin/students/import",
        data={"semester_id": "2", "csv_file": (BytesIO(csv_data), "students.csv")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/students?semester_id=2")
    assert captured["rows"][0]["register_number"] == "25MCA001"
    assert captured["rows"][0]["email"] == "student@example.com"


@pytest.mark.component
def test_bulk_import_reports_csv_row_errors_without_writing(client, monkeypatch):
    login_as(client, "ADMIN")
    monkeypatch.setattr(
        "services.academic_context_service.get_active_context",
        lambda semester_id: academic_contexts()[0],
    )
    monkeypatch.setattr(
        "services.student_service.bulk_create_students",
        lambda rows: pytest.fail("invalid CSV must not be written"),
    )
    csv_data = (
        b"register_number,full_name,email,initial_password\n"
        b"25MCA001,Student One,same@example.com,Student123\n"
        b"25MCA001,Student Two,same@example.com,short\n"
    )

    response = client.post(
        "/admin/students/import",
        data={"semester_id": "2", "csv_file": (BytesIO(csv_data), "students.csv")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert b"Row 3" in response.data
    assert b"duplicated in this file" in response.data

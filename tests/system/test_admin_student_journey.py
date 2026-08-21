import pytest


@pytest.mark.system
def test_admin_can_add_view_edit_and_deactivate_student(client, monkeypatch):
    students = []
    courses = [{"id": 1, "code": "MCA", "name": "Master of Computer Applications"}]
    semesters = [
        {
            "id": 2,
            "course_id": 1,
            "semester_number": 3,
            "section": "A",
            "academic_year": "2026-27",
        }
    ]

    def create_student(data):
        students.append(
            {
                "id": 1,
                "user_id": 20,
                **data,
                "face_registered": False,
                "is_active": True,
                "course_code": "MCA",
                "course_name": "Master of Computer Applications",
                "semester_number": 3,
                "section": "A",
                "academic_year": "2026-27",
            }
        )
        return 1

    def update_student(student_id, data):
        students[0].update(data)

    def set_active(student_id, active):
        students[0]["is_active"] = active

    monkeypatch.setattr("services.student_service.get_academic_options", lambda: (courses, semesters))
    monkeypatch.setattr("services.student_service.semester_belongs_to_course", lambda *args: True)
    monkeypatch.setattr("services.student_service.create_student", create_student)
    monkeypatch.setattr("services.student_service.list_students", lambda: students)
    monkeypatch.setattr("services.student_service.get_student", lambda student_id: students[0] if students else None)
    monkeypatch.setattr("services.student_service.update_student", update_student)
    monkeypatch.setattr("services.student_service.set_student_active", set_active)

    with client.session_transaction() as user_session:
        user_session["user_id"] = 1
        user_session["full_name"] = "Admin"
        user_session["role"] = "ADMIN"

    added = client.post(
        "/admin/students/add",
        data={
            "register_number": "23mca104",
            "full_name": "Test Student",
            "email": "student@example.com",
            "password": "Student@123",
            "course_id": "1",
            "semester_id": "2",
        },
        follow_redirects=True,
    )
    assert added.status_code == 200
    assert b"23MCA104" in added.data

    edited = client.post(
        "/admin/students/1/edit",
        data={
            "register_number": "23MCA104",
            "full_name": "Updated Student",
            "email": "updated@example.com",
            "password": "",
            "course_id": "1",
            "semester_id": "2",
        },
        follow_redirects=True,
    )
    assert edited.status_code == 200
    assert b"Updated Student" in edited.data
    assert b"Linked" in edited.data

    deactivated = client.post(
        "/admin/students/1/status",
        data={"is_active": "0"},
        follow_redirects=True,
    )
    assert deactivated.status_code == 200
    assert b"Inactive" in deactivated.data

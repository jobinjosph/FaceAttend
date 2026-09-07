import pytest


@pytest.mark.system
def test_admin_can_add_view_edit_and_graduate_student(client, monkeypatch):
    students = []
    contexts = [
        {
            "id": 2,
            "course_id": 1,
            "course_code": "MCA",
            "course_name": "Master of Computer Applications",
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
                "lifecycle_status": "ACTIVE",
                "course_code": "MCA",
                "course_name": "Master of Computer Applications",
                "semester_number": 3,
                "section": "A",
                "academic_year": "2026-27",
            }
        )
        return 1

    def update_student(student_id, data, moved_by_user_id=None):
        students[0].update(data)

    def set_lifecycle(student_id, status, admin):
        students[0]["lifecycle_status"] = status
        students[0]["is_active"] = status == "ACTIVE"

    monkeypatch.setattr("services.academic_context_service.list_active_contexts", lambda: contexts)
    monkeypatch.setattr("services.student_service.active_semester_belongs_to_course", lambda *args: True)
    monkeypatch.setattr("services.student_service.create_student", create_student)
    monkeypatch.setattr("services.student_service.list_students", lambda semester_id, status="ACTIVE": students)
    monkeypatch.setattr("services.student_service.get_student", lambda student_id: students[0] if students else None)
    monkeypatch.setattr("services.student_service.update_student", update_student)
    monkeypatch.setattr("services.student_service.set_student_lifecycle_status", set_lifecycle)

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

    graduated = client.post(
        "/admin/students/1/lifecycle",
        data={"lifecycle_status": "GRADUATED", "return_status": "ACTIVE"},
        follow_redirects=True,
    )
    assert graduated.status_code == 200
    assert b"Graduated" in graduated.data

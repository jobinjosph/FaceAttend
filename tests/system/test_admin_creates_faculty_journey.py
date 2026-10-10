import pytest

from services.auth_service import hash_password


@pytest.mark.system
def test_admin_creates_faculty_then_faculty_can_login(client, monkeypatch):
    faculty_rows = []
    faculty_user = {}

    def create_faculty(data):
        faculty_user.update(
            id=20,
            full_name=data["full_name"],
            email=data["email"],
            password_hash=hash_password(data["password"]),
            role="FACULTY",
            is_active=True,
        )
        faculty_rows.append(
            {
                "id": 10,
                "user_id": 20,
                "employee_code": data["employee_code"],
                "full_name": data["full_name"],
                "email": data["email"],
                "is_active": True,
            }
        )
        return 10

    monkeypatch.setattr("services.faculty_service.create_faculty", create_faculty)
    monkeypatch.setattr("services.faculty_service.list_faculty", lambda: faculty_rows)
    monkeypatch.setattr(
        "routes.auth.find_user_by_email",
        lambda email: faculty_user if email == faculty_user.get("email") else None,
    )

    with client.session_transaction() as user_session:
        user_session["user_id"] = 1
        user_session["full_name"] = "Admin"
        user_session["role"] = "ADMIN"

    created = client.post(
        "/admin/faculty/add",
        data={
            "employee_code": "FC001",
            "full_name": "New Faculty",
            "email": "faculty@example.com",
            "password": "FacultyPass123",
        },
        follow_redirects=True,
    )
    assert created.status_code == 200
    assert b"New Faculty" in created.data
    assert b"Created" in created.data

    client.post("/logout")
    logged_in = client.post(
        "/login",
        data={"email": "faculty@example.com", "password": "FacultyPass123"},
        follow_redirects=True,
    )
    assert logged_in.status_code == 200
    assert b"Welcome, New Faculty" in logged_in.data
    assert b"My Sessions" in logged_in.data

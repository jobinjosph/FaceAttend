import pytest

from services.auth_service import hash_password


@pytest.mark.system
def test_admin_can_login_view_dashboard_and_logout(client, monkeypatch):
    test_admin = {
        "id": 1,
        "full_name": "FaceAttend Admin",
        "email": "admin@faceattend.test",
        "password_hash": hash_password("AdminPass123"),
        "role": "ADMIN",
        "is_active": True,
    }
    monkeypatch.setattr("routes.auth.find_user_by_email", lambda email: test_admin)

    login_response = client.post(
        "/login",
        data={
            "email": "admin@faceattend.test",
            "password": "AdminPass123",
        },
        follow_redirects=True,
    )

    assert login_response.status_code == 200
    assert b"Welcome, FaceAttend Admin" in login_response.data
    assert b"Manage Students" in login_response.data

    logout_response = client.post("/logout", follow_redirects=True)
    assert logout_response.status_code == 200
    assert b"Smarter attendance." in logout_response.data

    protected_response = client.get("/dashboard/admin")
    assert protected_response.status_code == 302
    assert protected_response.headers["Location"].endswith("/login")

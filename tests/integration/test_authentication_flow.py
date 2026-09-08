import pytest
import mysql.connector

from services.auth_service import hash_password


def admin_user(active=True):
    return {
        "id": 1,
        "full_name": "Test Admin",
        "email": "admin@example.com",
        "password_hash": hash_password("AdminPass123"),
        "role": "ADMIN",
        "is_active": active,
    }


@pytest.mark.integration
def test_admin_login_creates_session_and_redirects(client, monkeypatch):
    monkeypatch.setattr("routes.auth.find_user_by_email", lambda email: admin_user())

    response = client.post(
        "/login",
        data={"email": "ADMIN@example.com", "password": "AdminPass123"},
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard/admin")
    with client.session_transaction() as user_session:
        assert user_session["user_id"] == 1
        assert user_session["role"] == "ADMIN"
        assert user_session["email"] == "admin@example.com"


@pytest.mark.integration
def test_second_login_is_blocked_until_current_user_logs_out(client, monkeypatch):
    with client.session_transaction() as user_session:
        user_session.update(
            user_id=1,
            full_name="Current Faculty",
            email="faculty@example.com",
            role="FACULTY",
        )

    lookup_called = False

    def find_second_user(email):
        nonlocal lookup_called
        lookup_called = True
        return admin_user()

    monkeypatch.setattr("routes.auth.find_user_by_email", find_second_user)
    response = client.post(
        "/login",
        data={"email": "admin@example.com", "password": "AdminPass123"},
    )

    assert response.status_code == 409
    assert b"Account already in use" in response.data
    assert b"Current Faculty" in response.data
    assert b"Logout to switch account" in response.data
    assert lookup_called is False
    with client.session_transaction() as user_session:
        assert user_session["user_id"] == 1
        assert user_session["role"] == "FACULTY"


@pytest.mark.integration
def test_user_can_login_with_another_account_after_logout(client, monkeypatch):
    with client.session_transaction() as user_session:
        user_session.update(user_id=4, full_name="Old User", role="FACULTY")

    client.post("/logout")
    monkeypatch.setattr("routes.auth.find_user_by_email", lambda email: admin_user())
    response = client.post(
        "/login",
        data={"email": "admin@example.com", "password": "AdminPass123"},
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard/admin")
    with client.session_transaction() as user_session:
        assert user_session["user_id"] == 1
        assert user_session["role"] == "ADMIN"


@pytest.mark.integration
def test_invalid_password_does_not_create_session(client, monkeypatch):
    monkeypatch.setattr("routes.auth.find_user_by_email", lambda email: admin_user())

    response = client.post(
        "/login",
        data={"email": "admin@example.com", "password": "WrongPassword"},
    )

    assert response.status_code == 401
    assert b"Incorrect email or password." in response.data
    with client.session_transaction() as user_session:
        assert "user_id" not in user_session


@pytest.mark.integration
def test_unknown_email_is_rejected(client, monkeypatch):
    monkeypatch.setattr("routes.auth.find_user_by_email", lambda email: None)

    response = client.post(
        "/login",
        data={"email": "unknown@example.com", "password": "SomePassword123"},
    )

    assert response.status_code == 401
    assert b"Incorrect email or password." in response.data


@pytest.mark.integration
def test_unknown_email_still_performs_password_hash_check(client, monkeypatch):
    captured = {}
    monkeypatch.setattr("routes.auth.find_user_by_email", lambda email: None)
    monkeypatch.setattr(
        "routes.auth.verify_password",
        lambda password_hash, password: captured.update(
            password_hash=password_hash, password=password
        ) or False,
    )

    response = client.post(
        "/login",
        data={"email": "unknown@example.com", "password": "SomePassword123"},
    )

    assert response.status_code == 401
    assert captured["password_hash"]
    assert captured["password"] == "SomePassword123"


@pytest.mark.integration
def test_login_database_failure_returns_controlled_error(client, monkeypatch):
    def raise_database_error(email):
        raise mysql.connector.Error("test database failure")

    monkeypatch.setattr("routes.auth.find_user_by_email", raise_database_error)

    response = client.post(
        "/login",
        data={"email": "admin@example.com", "password": "AdminPass123"},
    )

    assert response.status_code == 503
    assert b"Login is temporarily unavailable." in response.data
    assert b"test database failure" not in response.data


@pytest.mark.integration
def test_inactive_account_is_rejected(client, monkeypatch):
    monkeypatch.setattr(
        "routes.auth.find_user_by_email",
        lambda email: admin_user(active=False),
    )

    response = client.post(
        "/login",
        data={"email": "admin@example.com", "password": "AdminPass123"},
    )

    assert response.status_code == 403
    assert b"This account is inactive." in response.data


@pytest.mark.integration
def test_logout_clears_session(client):
    with client.session_transaction() as user_session:
        user_session["user_id"] = 1
        user_session["full_name"] = "Test Admin"
        user_session["role"] = "ADMIN"

    response = client.post("/logout")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")
    with client.session_transaction() as user_session:
        assert "user_id" not in user_session


@pytest.mark.integration
@pytest.mark.parametrize(
    ("role", "expected_path"),
    [
        ("ADMIN", "/dashboard/admin"),
        ("FACULTY", "/dashboard/faculty"),
        ("STUDENT", "/dashboard/student"),
    ],
)
def test_each_role_is_redirected_to_its_dashboard(
    client,
    monkeypatch,
    role,
    expected_path,
):
    user = admin_user()
    user["role"] = role
    monkeypatch.setattr("routes.auth.find_user_by_email", lambda email: user)

    response = client.post(
        "/login",
        data={"email": "user@example.com", "password": "AdminPass123"},
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith(expected_path)


@pytest.mark.integration
def test_unsupported_role_is_rejected(client, monkeypatch):
    user = admin_user()
    user["role"] = "UNKNOWN"
    monkeypatch.setattr("routes.auth.find_user_by_email", lambda email: user)

    response = client.post(
        "/login",
        data={"email": "user@example.com", "password": "AdminPass123"},
    )

    assert response.status_code == 403
    assert b"unsupported role" in response.data

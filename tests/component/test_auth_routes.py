import pytest


@pytest.mark.component
def test_login_page_opens(client):
    response = client.get("/login")

    assert response.status_code == 200
    assert b"Welcome back" in response.data
    assert b"Login securely" in response.data


@pytest.mark.component
def test_empty_login_form_is_rejected(client):
    response = client.post("/login", data={"email": "", "password": ""})

    assert response.status_code == 400
    assert b"Please enter both email and password." in response.data


@pytest.mark.component
def test_login_page_can_display_incorrect_password_message(client, monkeypatch):
    from services.auth_service import hash_password

    monkeypatch.setattr(
        "routes.auth.find_user_by_email",
        lambda email: {
            "id": 4,
            "full_name": "Faculty",
            "email": email,
            "password_hash": hash_password("CorrectPassword123"),
            "role": "FACULTY",
            "is_active": True,
        },
    )
    response = client.post(
        "/login",
        data={"email": "faculty@example.com", "password": "WrongPassword"},
    )

    assert response.status_code == 401
    assert b"Incorrect password. Please try again." in response.data


@pytest.mark.component
def test_logged_out_user_is_redirected_from_dashboard(client):
    response = client.get("/dashboard/admin")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


@pytest.mark.component
def test_student_is_forbidden_from_admin_dashboard(client):
    with client.session_transaction() as user_session:
        user_session["user_id"] = 3
        user_session["full_name"] = "Test Student"
        user_session["role"] = "STUDENT"

    response = client.get("/dashboard/admin")

    assert response.status_code == 403


@pytest.mark.component
@pytest.mark.parametrize(
    ("role", "allowed_path", "forbidden_paths"),
    [
        ("ADMIN", "/dashboard/admin", ["/dashboard/faculty", "/dashboard/student"]),
        ("FACULTY", "/dashboard/faculty", ["/dashboard/admin", "/dashboard/student"]),
        ("STUDENT", "/dashboard/student", ["/dashboard/admin", "/dashboard/faculty"]),
    ],
)
def test_roles_can_only_access_their_own_dashboard(
    client,
    role,
    allowed_path,
    forbidden_paths,
):
    with client.session_transaction() as user_session:
        user_session["user_id"] = 10
        user_session["full_name"] = "Role Test User"
        user_session["role"] = role

    allowed_response = client.get(allowed_path)
    assert allowed_response.status_code == 200
    assert b'class="account-menu"' in allowed_response.data
    assert b"Role Test User" in allowed_response.data
    assert b'class="account-logout"' in allowed_response.data
    for path in forbidden_paths:
        assert client.get(path).status_code == 403


@pytest.mark.component
@pytest.mark.parametrize(
    ("role", "expected_path"),
    [
        ("ADMIN", "/dashboard/admin"),
        ("FACULTY", "/dashboard/faculty"),
        ("STUDENT", "/dashboard/student"),
    ],
)
def test_logged_in_user_sees_logout_prompt_instead_of_second_login(client, role, expected_path):
    with client.session_transaction() as user_session:
        user_session["user_id"] = 11
        user_session["full_name"] = "Logged In User"
        user_session["role"] = role

    response = client.get("/login")

    assert response.status_code == 200
    assert b"Account already in use" in response.data
    assert b"Logged In User" in response.data
    assert b"Logout to switch account" in response.data
    assert b'class="apple-shop-button"' in response.data
    assert b"Continue with current account" in response.data
    assert expected_path.encode() in response.data
    assert b"Login securely" not in response.data

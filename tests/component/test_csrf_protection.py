import pytest

from app import create_app


@pytest.fixture()
def csrf_client():
    app = create_app(
        {
            "TESTING": True,
            "DEBUG": False,
            "SECRET_KEY": "csrf-test-secret",
            "WTF_CSRF_ENABLED": True,
        }
    )
    return app.test_client()


@pytest.mark.component
def test_login_post_without_csrf_token_is_blocked(csrf_client):
    response = csrf_client.post(
        "/login",
        data={"email": "admin@example.com", "password": "AdminPass123"},
    )

    assert response.status_code == 400


@pytest.mark.component
def test_logout_post_without_csrf_token_is_blocked(csrf_client):
    with csrf_client.session_transaction() as user_session:
        user_session["user_id"] = 1
        user_session["role"] = "ADMIN"

    response = csrf_client.post("/logout")

    assert response.status_code == 400

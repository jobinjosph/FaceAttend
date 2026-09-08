import pytest

from app import create_app


@pytest.mark.unit
def test_app_factory_accepts_test_configuration():
    app = create_app(
        {
            "TESTING": True,
            "DEBUG": False,
            "SECRET_KEY": "unit-test-secret",
        }
    )

    assert app.config["TESTING"] is True
    assert app.config["DEBUG"] is False
    assert app.config["SECRET_KEY"] == "unit-test-secret"


def test_camera_uploads_have_a_request_size_limit():
    app = create_app({"TESTING": True})
    assert app.config["MAX_CONTENT_LENGTH"] == 8 * 1024 * 1024


@pytest.mark.unit
def test_secure_session_cookie_defaults_are_enabled():
    app = create_app({"TESTING": True})

    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert app.permanent_session_lifetime.total_seconds() == 8 * 60 * 60


@pytest.mark.unit
def test_responses_include_security_headers_and_private_pages_are_not_cached():
    app = create_app({"TESTING": True, "SECRET_KEY": "header-test-secret"})
    client = app.test_client()

    public_response = client.get("/")
    assert public_response.headers["X-Content-Type-Options"] == "nosniff"
    assert public_response.headers["X-Frame-Options"] == "DENY"
    assert public_response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert public_response.headers["Permissions-Policy"] == "camera=(self), microphone=(), geolocation=()"

    with client.session_transaction() as user_session:
        user_session.update(user_id=1, role="ADMIN")
    private_response = client.get("/dashboard/admin")
    assert private_response.headers["Cache-Control"] == "no-store, private"
    assert private_response.headers["Pragma"] == "no-cache"

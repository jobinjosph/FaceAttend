import pytest

from app import create_app


@pytest.fixture()
def app():
    """Create an isolated Flask application for each test."""
    application = create_app(
        {
            "TESTING": True,
            "DEBUG": False,
            "SECRET_KEY": "test-secret-key",
            "DB_NAME": "faceattend_test",
        }
    )

    yield application


@pytest.fixture()
def client(app):
    """Return Flask's browser-like test client."""
    return app.test_client()

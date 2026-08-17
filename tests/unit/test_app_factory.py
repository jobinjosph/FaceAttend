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

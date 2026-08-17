import pytest
import mysql.connector


@pytest.mark.component
def test_create_admin_command_is_registered_and_creates_admin(app, monkeypatch):
    captured = {}

    def fake_create_user(name, email, password, role):
        captured.update(
            name=name,
            email=email,
            password=password,
            role=role,
        )
        return 7

    monkeypatch.setattr("services.auth_service.create_user", fake_create_user)
    runner = app.test_cli_runner()

    result = runner.invoke(
        args=[
            "create-admin",
            "--name",
            "Test Admin",
            "--email",
            "admin@example.com",
            "--password",
            "AdminPass123",
        ]
    )

    assert result.exit_code == 0
    assert "Admin created successfully with user ID 7." in result.output
    assert captured == {
        "name": "Test Admin",
        "email": "admin@example.com",
        "password": "AdminPass123",
        "role": "ADMIN",
    }


@pytest.mark.component
def test_create_admin_command_rejects_short_password(app):
    runner = app.test_cli_runner()

    result = runner.invoke(
        args=[
            "create-admin",
            "--name",
            "Test Admin",
            "--email",
            "admin@example.com",
            "--password",
            "short",
        ]
    )

    assert result.exit_code != 0
    assert "Password must contain at least 8 characters." in result.output


@pytest.mark.component
def test_create_admin_command_rejects_duplicate_email(app, monkeypatch):
    def duplicate_user(*args, **kwargs):
        raise mysql.connector.IntegrityError("duplicate email")

    monkeypatch.setattr("services.auth_service.create_user", duplicate_user)
    runner = app.test_cli_runner()

    result = runner.invoke(
        args=[
            "create-admin",
            "--name",
            "Duplicate Admin",
            "--email",
            "admin@example.com",
            "--password",
            "AdminPass123",
        ]
    )

    assert result.exit_code != 0
    assert "A user with that email already exists." in result.output

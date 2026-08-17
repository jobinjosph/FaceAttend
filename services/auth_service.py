import click
import mysql.connector
from flask import current_app
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_db_connection


VALID_ROLES = {"ADMIN", "FACULTY", "STUDENT"}


def hash_password(password):
    """Return a secure, salted password hash."""
    return generate_password_hash(password)


def verify_password(password_hash, password):
    """Safely compare a password with its stored hash."""
    if not password_hash or not password:
        return False
    return check_password_hash(password_hash, password)


def find_user_by_email(email):
    """Return one user as a dictionary, or None when it does not exist."""
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id, full_name, email, password_hash, role, is_active
            FROM users
            WHERE email = %s
            LIMIT 1
            """,
            (email.strip().lower(),),
        )
        return cursor.fetchone()
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def create_user(full_name, email, password, role):
    """Create a user with a hashed password and return the new user ID."""
    normalized_role = role.strip().upper()
    if normalized_role not in VALID_ROLES:
        raise ValueError(f"Unsupported role: {role}")

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO users (full_name, email, password_hash, role)
            VALUES (%s, %s, %s, %s)
            """,
            (
                full_name.strip(),
                email.strip().lower(),
                hash_password(password),
                normalized_role,
            ),
        )
        connection.commit()
        return cursor.lastrowid
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def register_auth_commands(app):
    @app.cli.command("create-admin")
    @click.option("--name", prompt="Full name")
    @click.option("--email", prompt="Email")
    @click.option(
        "--password",
        prompt=True,
        hide_input=True,
        confirmation_prompt=True,
    )
    def create_admin_command(name, email, password):
        """Create FaceAttend's first administrator account."""
        if len(password) < 8:
            raise click.ClickException("Password must contain at least 8 characters.")

        try:
            user_id = create_user(name, email, password, "ADMIN")
        except mysql.connector.IntegrityError:
            raise click.ClickException("A user with that email already exists.") from None
        except mysql.connector.Error as exc:
            current_app.logger.error("Could not create admin: %s", exc)
            raise click.ClickException("Could not create the admin account.") from None

        click.echo(f"Admin created successfully with user ID {user_id}.")

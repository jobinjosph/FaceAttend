import re

from db import get_db_connection
from services.auth_service import hash_password


EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def normalize_employee_code(value):
    return "".join(value.strip().upper().split())


def normalize_faculty_data(form_data):
    return {
        "employee_code": normalize_employee_code(form_data.get("employee_code", "")),
        "full_name": " ".join(form_data.get("full_name", "").strip().split()),
        "email": form_data.get("email", "").strip().lower(),
        "password": form_data.get("password", ""),
    }


def validate_faculty_data(data, require_password=False):
    errors = {}

    if not data["employee_code"]:
        errors["employee_code"] = "Employee code is required."
    elif len(data["employee_code"]) > 50:
        errors["employee_code"] = "Employee code is too long."

    if not data["full_name"]:
        errors["full_name"] = "Faculty name is required."
    elif len(data["full_name"]) > 150:
        errors["full_name"] = "Faculty name is too long."

    if not data["email"]:
        errors["email"] = "Email address is required for faculty login."
    elif not EMAIL_PATTERN.fullmatch(data["email"]):
        errors["email"] = "Enter a valid email address."

    if require_password and not data["password"]:
        errors["password"] = "An initial password is required."
    elif data["password"] and len(data["password"]) < 8:
        errors["password"] = "Password must contain at least 8 characters."

    return errors


def list_faculty():
    return _fetch_all(
        """
        SELECT f.id, f.employee_code, f.full_name, f.email, f.is_active,
               f.user_id
        FROM faculty f
        LEFT JOIN users u ON u.id = f.user_id
        ORDER BY f.full_name, f.employee_code
        """
    )


def get_faculty(faculty_id):
    return _fetch_one(
        """
        SELECT id, user_id, employee_code, full_name, email, is_active
        FROM faculty
        WHERE id = %s
        """,
        (faculty_id,),
    )


def create_faculty(data):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO users (full_name, email, password_hash, role, is_active)
            VALUES (%s, %s, %s, 'FACULTY', TRUE)
            """,
            (data["full_name"], data["email"], hash_password(data["password"])),
        )
        user_id = cursor.lastrowid
        cursor.execute(
            """
            INSERT INTO faculty
                (user_id, employee_code, full_name, email, is_active)
            VALUES (%s, %s, %s, %s, TRUE)
            """,
            (user_id, data["employee_code"], data["full_name"], data["email"]),
        )
        faculty_id = cursor.lastrowid
        connection.commit()
        return faculty_id
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def update_faculty(faculty_id, data):
    faculty = get_faculty(faculty_id)
    if faculty is None:
        return False

    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            UPDATE faculty
            SET employee_code = %s, full_name = %s, email = %s
            WHERE id = %s
            """,
            (data["employee_code"], data["full_name"], data["email"], faculty_id),
        )

        if faculty["user_id"]:
            if data["password"]:
                cursor.execute(
                    """
                    UPDATE users
                    SET full_name = %s, email = %s, password_hash = %s
                    WHERE id = %s
                    """,
                    (
                        data["full_name"],
                        data["email"],
                        hash_password(data["password"]),
                        faculty["user_id"],
                    ),
                )
            else:
                cursor.execute(
                    "UPDATE users SET full_name = %s, email = %s WHERE id = %s",
                    (data["full_name"], data["email"], faculty["user_id"]),
                )

        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def set_faculty_active(faculty_id, is_active):
    faculty = get_faculty(faculty_id)
    if faculty is None:
        return False

    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "UPDATE faculty SET is_active = %s WHERE id = %s",
            (bool(is_active), faculty_id),
        )
        if faculty["user_id"]:
            cursor.execute(
                "UPDATE users SET is_active = %s WHERE id = %s",
                (bool(is_active), faculty["user_id"]),
            )
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def _fetch_all(query, params=()):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def _fetch_one(query, params=()):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        return cursor.fetchone()
    finally:
        cursor.close()
        connection.close()

import re

from db import get_db_connection


EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def normalize_register_number(value):
    return "".join(value.strip().upper().split())


def normalize_student_data(form_data):
    return {
        "register_number": normalize_register_number(
            form_data.get("register_number", "")
        ),
        "full_name": " ".join(form_data.get("full_name", "").strip().split()),
        "email": form_data.get("email", "").strip().lower(),
        "course_id": form_data.get("course_id", "").strip(),
        "semester_id": form_data.get("semester_id", "").strip(),
    }


def validate_student_data(data):
    errors = {}

    if not data["register_number"]:
        errors["register_number"] = "Register number is required."
    elif len(data["register_number"]) > 50:
        errors["register_number"] = "Register number is too long."

    if not data["full_name"]:
        errors["full_name"] = "Student name is required."
    elif len(data["full_name"]) > 150:
        errors["full_name"] = "Student name is too long."

    if data["email"] and not EMAIL_PATTERN.fullmatch(data["email"]):
        errors["email"] = "Enter a valid email address."

    for field, label in (("course_id", "Course"), ("semester_id", "Semester")):
        try:
            value = int(data[field])
            if value < 1:
                raise ValueError
            data[field] = value
        except (TypeError, ValueError):
            errors[field] = f"{label} is required."

    return errors


def list_students():
    query = """
        SELECT s.id, s.register_number, s.full_name, s.email,
               s.face_registered, s.is_active,
               c.code AS course_code, c.name AS course_name,
               sem.semester_number, sem.section, sem.academic_year
        FROM students s
        JOIN courses c ON c.id = s.course_id
        JOIN semesters sem ON sem.id = s.semester_id
        ORDER BY s.full_name, s.register_number
    """
    return _fetch_all(query)


def get_student(student_id):
    query = """
        SELECT id, register_number, full_name, email, course_id, semester_id,
               face_registered, is_active
        FROM students
        WHERE id = %s
    """
    return _fetch_one(query, (student_id,))


def get_academic_options():
    courses = _fetch_all("SELECT id, code, name FROM courses ORDER BY code")
    semesters = _fetch_all(
        """
        SELECT id, course_id, semester_number, section, academic_year
        FROM semesters
        ORDER BY course_id, semester_number, section
        """
    )
    return courses, semesters


def semester_belongs_to_course(semester_id, course_id):
    result = _fetch_one(
        "SELECT id FROM semesters WHERE id = %s AND course_id = %s",
        (semester_id, course_id),
    )
    return result is not None


def create_student(data):
    query = """
        INSERT INTO students
            (register_number, full_name, email, course_id, semester_id)
        VALUES (%s, %s, %s, %s, %s)
    """
    return _execute_write(
        query,
        (
            data["register_number"],
            data["full_name"],
            data["email"] or None,
            data["course_id"],
            data["semester_id"],
        ),
    )


def update_student(student_id, data):
    query = """
        UPDATE students
        SET register_number = %s, full_name = %s, email = %s,
            course_id = %s, semester_id = %s
        WHERE id = %s
    """
    _execute_write(
        query,
        (
            data["register_number"],
            data["full_name"],
            data["email"] or None,
            data["course_id"],
            data["semester_id"],
            student_id,
        ),
    )


def set_student_active(student_id, is_active):
    _execute_write(
        "UPDATE students SET is_active = %s WHERE id = %s",
        (bool(is_active), student_id),
    )


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


def _execute_write(query, params):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(query, params)
        connection.commit()
        return cursor.lastrowid
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()

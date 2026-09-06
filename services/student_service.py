import re

from db import get_db_connection
from services.auth_service import hash_password


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
        "password": form_data.get("password", ""),
        "course_id": form_data.get("course_id", "").strip(),
        "semester_id": form_data.get("semester_id", "").strip(),
    }


def validate_student_data(data, require_password=False):
    errors = {}

    if not data["register_number"]:
        errors["register_number"] = "Register number is required."
    elif len(data["register_number"]) > 50:
        errors["register_number"] = "Register number is too long."

    if not data["full_name"]:
        errors["full_name"] = "Student name is required."
    elif len(data["full_name"]) > 150:
        errors["full_name"] = "Student name is too long."

    if not data["email"]:
        errors["email"] = "Student login email is required."
    elif not EMAIL_PATTERN.fullmatch(data["email"]):
        errors["email"] = "Enter a valid email address."

    if require_password and not data["password"]:
        errors["password"] = "An initial password is required."
    elif data["password"] and len(data["password"]) < 8:
        errors["password"] = "Password must be at least 8 characters."

    for field, label in (("course_id", "Course"), ("semester_id", "Semester")):
        try:
            value = int(data[field])
            if value < 1:
                raise ValueError
            data[field] = value
        except (TypeError, ValueError):
            errors[field] = f"{label} is required."

    return errors


def list_students(semester_id):
    query = """
        SELECT s.id, s.user_id, s.register_number, s.full_name, s.email,
               s.face_registered, s.is_active,
               c.code AS course_code, c.name AS course_name,
               sem.semester_number, sem.section, sem.academic_year
        FROM students s
        JOIN courses c ON c.id = s.course_id
        JOIN semesters sem ON sem.id = s.semester_id
        WHERE s.semester_id = %s
        ORDER BY s.full_name, s.register_number
    """
    return _fetch_all(query, (semester_id,))


def get_student(student_id):
    query = """
        SELECT id, user_id, register_number, full_name, email, course_id, semester_id,
               face_registered, is_active
        FROM students
        WHERE id = %s
    """
    return _fetch_one(query, (student_id,))


def get_placement_history(student_id):
    return _fetch_all(
        """SELECT h.id, h.moved_at,
                  from_course.code AS from_course_code,
                  from_course.name AS from_course_name,
                  from_sem.academic_year AS from_academic_year,
                  from_sem.semester_number AS from_semester_number,
                  from_sem.section AS from_section,
                  to_course.code AS to_course_code,
                  to_course.name AS to_course_name,
                  to_sem.academic_year AS to_academic_year,
                  to_sem.semester_number AS to_semester_number,
                  to_sem.section AS to_section,
                  mover.full_name AS moved_by_name
           FROM student_placement_history h
           JOIN semesters from_sem ON from_sem.id=h.from_semester_id
           JOIN courses from_course ON from_course.id=from_sem.course_id
           JOIN semesters to_sem ON to_sem.id=h.to_semester_id
           JOIN courses to_course ON to_course.id=to_sem.course_id
           LEFT JOIN users mover ON mover.id=h.moved_by_user_id
           WHERE h.student_id=%s
           ORDER BY h.moved_at DESC, h.id DESC""",
        (student_id,),
    )


def active_semester_belongs_to_course(semester_id, course_id):
    result = _fetch_one(
        """SELECT sem.id FROM semesters sem
           JOIN courses c ON c.id=sem.course_id
           WHERE sem.id=%s AND sem.course_id=%s
             AND sem.is_active=TRUE AND c.is_active=TRUE""",
        (semester_id, course_id),
    )
    return result is not None


def create_student(data):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO users (full_name, email, password_hash, role, is_active)
            VALUES (%s, %s, %s, 'STUDENT', TRUE)
            """,
            (data["full_name"], data["email"], hash_password(data["password"])),
        )
        user_id = cursor.lastrowid
        cursor.execute(
            """
            INSERT INTO students
                (user_id, register_number, full_name, email, course_id, semester_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                data["register_number"],
                data["full_name"],
                data["email"],
                data["course_id"],
                data["semester_id"],
            ),
        )
        student_id = cursor.lastrowid
        connection.commit()
        return student_id
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def update_student(student_id, data, moved_by_user_id=None):
    student = get_student(student_id)
    if student is None:
        return

    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        user_id = student.get("user_id")
        if user_id:
            if data["password"]:
                cursor.execute(
                    """
                    UPDATE users
                    SET full_name = %s, email = %s, password_hash = %s
                    WHERE id = %s
                    """,
                    (
                        data["full_name"], data["email"],
                        hash_password(data["password"]), user_id,
                    ),
                )
            else:
                cursor.execute(
                    "UPDATE users SET full_name = %s, email = %s WHERE id = %s",
                    (data["full_name"], data["email"], user_id),
                )
        else:
            cursor.execute(
                """
                INSERT INTO users (full_name, email, password_hash, role, is_active)
                VALUES (%s, %s, %s, 'STUDENT', %s)
                """,
                (
                    data["full_name"], data["email"],
                    hash_password(data["password"]), bool(student["is_active"]),
                ),
            )
            user_id = cursor.lastrowid

        previous_semester_id = student.get("semester_id")
        if previous_semester_id is not None and previous_semester_id != data["semester_id"]:
            cursor.execute(
                """INSERT INTO student_placement_history
                       (student_id, from_semester_id, to_semester_id, moved_by_user_id)
                   VALUES (%s, %s, %s, %s)""",
                (student_id, previous_semester_id, data["semester_id"], moved_by_user_id),
            )

        cursor.execute(
            """
            UPDATE students
            SET user_id = %s, register_number = %s, full_name = %s, email = %s,
                course_id = %s, semester_id = %s
            WHERE id = %s
            """,
            (
                user_id, data["register_number"], data["full_name"], data["email"],
                data["course_id"], data["semester_id"], student_id,
            ),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def set_student_active(student_id, is_active):
    student = get_student(student_id)
    if student is None:
        return

    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "UPDATE students SET is_active = %s WHERE id = %s",
            (bool(is_active), student_id),
        )
        if student.get("user_id"):
            cursor.execute(
                "UPDATE users SET is_active = %s WHERE id = %s",
                (bool(is_active), student["user_id"]),
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def move_students(student_ids, source_semester_id, destination_semester_id, moved_by_user_id):
    student_ids = list(dict.fromkeys(student_ids))
    if not student_ids:
        raise ValueError("Select at least one student.")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    placeholders = ", ".join(["%s"] * len(student_ids))
    try:
        cursor.execute(
            """SELECT sem.id, sem.course_id FROM semesters sem
               JOIN courses c ON c.id=sem.course_id
               WHERE sem.id=%s AND sem.is_active=TRUE AND c.is_active=TRUE
               FOR UPDATE""",
            (destination_semester_id,),
        )
        destination = cursor.fetchone()
        if destination is None:
            raise ValueError("The selected destination is not active.")
        if destination_semester_id == source_semester_id:
            raise ValueError("Select a destination different from the current group.")

        cursor.execute(
            f"SELECT id, semester_id FROM students WHERE id IN ({placeholders}) FOR UPDATE",
            tuple(student_ids),
        )
        selected_students = cursor.fetchall()
        if len(selected_students) != len(student_ids):
            raise ValueError("One or more selected students no longer exist.")
        if any(item["semester_id"] != source_semester_id for item in selected_students):
            raise ValueError("One or more selected students are no longer in this group. Refresh and try again.")

        history_rows = [
            (item["id"], source_semester_id, destination_semester_id, moved_by_user_id)
            for item in selected_students
        ]
        cursor.executemany(
            """INSERT INTO student_placement_history
                   (student_id, from_semester_id, to_semester_id, moved_by_user_id)
               VALUES (%s, %s, %s, %s)""",
            history_rows,
        )
        cursor.execute(
            f"UPDATE students SET course_id=%s, semester_id=%s WHERE id IN ({placeholders})",
            (destination["course_id"], destination_semester_id, *student_ids),
        )
        connection.commit()
        return len(student_ids)
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

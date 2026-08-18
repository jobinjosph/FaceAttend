from db import get_db_connection


def normalize_assignment_data(form_data):
    data = {}
    for field in ("subject_id", "faculty_id"):
        try:
            data[field] = int(form_data.get(field, ""))
        except (TypeError, ValueError):
            data[field] = None
    return data


def validate_assignment_data(data):
    errors = {}
    if not data["subject_id"]:
        errors["subject_id"] = "Select a subject."
    if not data["faculty_id"]:
        errors["faculty_id"] = "Select a faculty member."
    return errors


def list_assignments():
    return _fetch_all(
        """
        SELECT a.id, s.id AS subject_id, s.subject_code, s.subject_name,
               f.id AS faculty_id, f.employee_code, f.full_name, f.email
        FROM faculty_subject_assignments a
        JOIN subjects s ON s.id = a.subject_id
        JOIN semesters sem ON sem.id = s.semester_id
        JOIN courses c ON c.id = sem.course_id
        JOIN faculty f ON f.id = a.faculty_id
        WHERE c.code = 'MCA' AND sem.semester_number = 3
        ORDER BY s.subject_code, f.full_name
        """
    )


def get_assignment_options():
    subjects = _fetch_all(
        """
        SELECT s.id, s.subject_code, s.subject_name
        FROM subjects s
        JOIN semesters sem ON sem.id = s.semester_id
        JOIN courses c ON c.id = sem.course_id
        WHERE c.code = 'MCA' AND sem.semester_number = 3 AND s.is_active = TRUE
        ORDER BY s.subject_code
        """
    )
    faculty = _fetch_all(
        """
        SELECT id, employee_code, full_name, email
        FROM faculty
        WHERE is_active = TRUE
        ORDER BY full_name, employee_code
        """
    )
    return subjects, faculty


def active_subject_exists(subject_id):
    return _fetch_one(
        """
        SELECT s.id
        FROM subjects s
        JOIN semesters sem ON sem.id = s.semester_id
        JOIN courses c ON c.id = sem.course_id
        WHERE s.id = %s AND s.is_active = TRUE
          AND c.code = 'MCA' AND sem.semester_number = 3
        """,
        (subject_id,),
    ) is not None


def active_faculty_exists(faculty_id):
    return _fetch_one(
        "SELECT id FROM faculty WHERE id = %s AND is_active = TRUE",
        (faculty_id,),
    ) is not None


def create_assignment(data):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "INSERT INTO faculty_subject_assignments (subject_id, faculty_id) VALUES (%s, %s)",
            (data["subject_id"], data["faculty_id"]),
        )
        connection.commit()
        return cursor.lastrowid
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def get_assignment(assignment_id):
    return _fetch_one(
        "SELECT id, subject_id, faculty_id FROM faculty_subject_assignments WHERE id = %s",
        (assignment_id,),
    )


def delete_assignment(assignment_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("DELETE FROM faculty_subject_assignments WHERE id = %s", (assignment_id,))
        connection.commit()
        return cursor.rowcount > 0
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

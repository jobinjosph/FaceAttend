from db import get_db_connection


ACTIVITY_TYPES = ("LECTURE", "THEORY", "PRACTICAL", "PROJECT")


def normalize_subject_data(form_data):
    return {
        "subject_code": "".join(form_data.get("subject_code", "").strip().upper().split()),
        "subject_name": " ".join(form_data.get("subject_name", "").strip().split()),
        "activity_type": form_data.get("activity_type", "LECTURE").strip().upper(),
    }


def validate_subject_data(data):
    errors = {}
    if not data["subject_code"]:
        errors["subject_code"] = "Subject code is required."
    elif len(data["subject_code"]) > 50:
        errors["subject_code"] = "Subject code is too long."

    if not data["subject_name"]:
        errors["subject_name"] = "Subject name is required."
    elif len(data["subject_name"]) > 160:
        errors["subject_name"] = "Subject name is too long."

    if data["activity_type"] not in ACTIVITY_TYPES:
        errors["activity_type"] = "Select a valid activity type."
    return errors


def get_mca_semester_three():
    return _fetch_one(
        """
        SELECT sem.id, sem.semester_number, sem.section, sem.academic_year,
               c.id AS course_id, c.code AS course_code, c.name AS course_name
        FROM semesters sem
        JOIN courses c ON c.id = sem.course_id
        WHERE c.code = 'MCA' AND sem.semester_number = 3
        ORDER BY sem.academic_year DESC, sem.section
        LIMIT 1
        """
    )


def list_semester_three_subjects(search="", status="all"):
    conditions = ["c.code = 'MCA'", "sem.semester_number = 3"]
    params = []
    if search:
        conditions.append("(s.subject_code LIKE %s OR s.subject_name LIKE %s)")
        term = f"%{search}%"
        params.extend((term, term))
    if status == "active":
        conditions.append("s.is_active = TRUE")
    elif status == "inactive":
        conditions.append("s.is_active = FALSE")

    return _fetch_all(
        f"""
        SELECT s.id, s.subject_code, s.subject_name, s.activity_type, s.is_active,
               sem.semester_number, sem.section, sem.academic_year,
               c.code AS course_code
        FROM subjects s
        JOIN semesters sem ON sem.id = s.semester_id
        JOIN courses c ON c.id = sem.course_id
        WHERE {' AND '.join(conditions)}
        ORDER BY s.subject_code
        """,
        tuple(params),
    )


def get_subject(subject_id):
    return _fetch_one(
        """
        SELECT s.id, s.subject_code, s.subject_name, s.activity_type, s.is_active,
               s.semester_id, sem.semester_number, c.code AS course_code
        FROM subjects s
        JOIN semesters sem ON sem.id = s.semester_id
        JOIN courses c ON c.id = sem.course_id
        WHERE s.id = %s AND c.code = 'MCA' AND sem.semester_number = 3
        """,
        (subject_id,),
    )


def create_subject(data, semester_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO subjects
                (subject_code, subject_name, semester_id, activity_type, is_active)
            VALUES (%s, %s, %s, %s, TRUE)
            """,
            (data["subject_code"], data["subject_name"], semester_id, data["activity_type"]),
        )
        connection.commit()
        return cursor.lastrowid
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def update_subject(subject_id, data):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            UPDATE subjects SET subject_code = %s, subject_name = %s, activity_type = %s
            WHERE id = %s
            """,
            (data["subject_code"], data["subject_name"], data["activity_type"], subject_id),
        )
        connection.commit()
        return cursor.rowcount > 0
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def set_subject_active(subject_id, is_active):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "UPDATE subjects SET is_active = %s WHERE id = %s",
            (bool(is_active), subject_id),
        )
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

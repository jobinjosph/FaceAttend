from datetime import date

from db import get_db_connection


STATUSES = ("SCHEDULED", "ACTIVE", "REVIEW", "CONFIRMED", "NOT_CONDUCTED")


def parse_session_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def generate_sessions(session_date, semester_id=None):
    day_of_week = session_date.isoweekday()
    if day_of_week > 6:
        return 0
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            INSERT IGNORE INTO attendance_sessions
                (semester_id, subject_id, faculty_id, timetable_period_id,
                 session_date, period_number, scheduled_start, scheduled_end, status)
            SELECT tp.semester_id, tp.subject_id, tp.faculty_id, tp.id,
                   %s, tp.period_number, tp.start_time, tp.end_time, 'SCHEDULED'
            FROM timetable_periods tp
            JOIN semesters sem ON sem.id = tp.semester_id
            JOIN courses c ON c.id = sem.course_id
            WHERE tp.day_of_week = %s AND tp.subject_id IS NOT NULL
              AND tp.faculty_id IS NOT NULL
              AND ((%s IS NULL AND c.code = 'MCA' AND sem.semester_number = 3) OR sem.id = %s)
            """,
            (session_date, day_of_week, semester_id, semester_id),
        )
        count = cursor.rowcount
        connection.commit()
        return count
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def list_sessions(session_date, semester_id=None):
    return _fetch_all(
        """
        SELECT ats.id, ats.session_date, ats.period_number, ats.status,
               TIME_FORMAT(ats.scheduled_start, '%H:%i') AS scheduled_start,
               TIME_FORMAT(ats.scheduled_end, '%H:%i') AS scheduled_end,
               ats.started_at, ats.ended_at, s.subject_code, s.subject_name,
               f.employee_code, f.full_name
        FROM attendance_sessions ats
        JOIN subjects s ON s.id = ats.subject_id
        JOIN faculty f ON f.id = ats.faculty_id
        JOIN semesters sem ON sem.id = ats.semester_id
        JOIN courses c ON c.id = sem.course_id
        WHERE ats.session_date = %s
          AND ((%s IS NULL AND c.code = 'MCA' AND sem.semester_number = 3) OR sem.id = %s)
        ORDER BY ats.period_number, ats.scheduled_start
        """,
        (session_date, semester_id, semester_id),
    )


def list_faculty_sessions(user_id, session_date):
    return _fetch_all(
        """
        SELECT ats.id, ats.session_date, ats.period_number, ats.status,
               TIME_FORMAT(ats.scheduled_start, '%H:%i') AS scheduled_start,
               TIME_FORMAT(ats.scheduled_end, '%H:%i') AS scheduled_end,
               ats.started_at, ats.ended_at, s.subject_code, s.subject_name
        FROM attendance_sessions ats
        JOIN subjects s ON s.id = ats.subject_id
        JOIN faculty f ON f.id = ats.faculty_id
        WHERE f.user_id = %s AND ats.session_date = %s
        ORDER BY ats.period_number, ats.scheduled_start
        """,
        (user_id, session_date),
    )


def get_faculty_session(session_id, user_id):
    return _fetch_one(
        """SELECT ats.id, ats.faculty_id, ats.status
           FROM attendance_sessions ats
           JOIN faculty f ON f.id = ats.faculty_id
           WHERE ats.id = %s AND f.user_id = %s""",
        (session_id, user_id),
    )


def start_session(session_id, user_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """SELECT ats.id, ats.faculty_id, ats.semester_id, ats.status FROM attendance_sessions ats
               JOIN faculty f ON f.id=ats.faculty_id
               WHERE ats.id=%s AND f.user_id=%s FOR UPDATE""",
            (session_id, user_id),
        )
        current = cursor.fetchone()
        if current is None:
            return "not_found"
        if current["status"] != "SCHEDULED":
            return "invalid_status"
        cursor.execute(
            "SELECT id FROM attendance_sessions WHERE faculty_id=%s AND status='ACTIVE' AND id<>%s LIMIT 1",
            (current["faculty_id"], session_id),
        )
        if cursor.fetchone():
            return "already_active"
        cursor.execute("UPDATE attendance_sessions SET status='ACTIVE', started_at=NOW() WHERE id=%s", (session_id,))
        cursor.execute(
            """INSERT IGNORE INTO attendance_records
               (session_id, student_id, status, marking_method)
               SELECT %s, st.id, 'NOT_MARKED', 'MANUAL'
               FROM students st
               WHERE st.semester_id=%s AND st.is_active=TRUE""",
            (session_id, current["semester_id"]),
        )
        connection.commit()
        return "started"
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def transition_session(session_id, user_id, expected_status, new_status):
    if expected_status not in STATUSES or new_status not in STATUSES:
        return False
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        end_sql = ", ended_at=NOW()" if expected_status == "ACTIVE" and new_status == "REVIEW" else ""
        cursor.execute(
            f"""UPDATE attendance_sessions ats JOIN faculty f ON f.id=ats.faculty_id
                SET ats.status=%s{end_sql}
                WHERE ats.id=%s AND f.user_id=%s AND ats.status=%s""",
            (new_status, session_id, user_id, expected_status),
        )
        connection.commit()
        return cursor.rowcount > 0
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def has_unmarked_records(session_id):
    row = _fetch_one(
        "SELECT COUNT(*) AS total FROM attendance_records WHERE session_id=%s AND status='NOT_MARKED'",
        (session_id,),
    )
    return bool(row and row["total"])


def _fetch_all(query, params=()):
    connection = get_db_connection(); cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(query, params); return cursor.fetchall()
    finally:
        cursor.close(); connection.close()


def _fetch_one(query, params=()):
    connection = get_db_connection(); cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(query, params); return cursor.fetchone()
    finally:
        cursor.close(); connection.close()

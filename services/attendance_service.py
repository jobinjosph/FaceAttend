from db import get_db_connection


MANUAL_STATUSES = ("PRESENT", "ABSENT", "LATE", "LEFT_EARLY", "NOT_MARKED")
EDITABLE_SESSION_STATUSES = ("ACTIVE", "REVIEW")


def normalize_attendance_data(form_data):
    return {
        "status": form_data.get("status", "").strip().upper(),
        "notes": " ".join(form_data.get("notes", "").strip().split()),
    }


def validate_attendance_data(data):
    errors = {}
    if data["status"] not in MANUAL_STATUSES:
        errors["status"] = "Select a valid attendance status."
    if len(data["notes"]) > 255:
        errors["notes"] = "Notes must contain no more than 255 characters."
    return errors


def normalize_bulk_attendance(form_data, student_ids):
    return {
        student_id: normalize_attendance_data(
            {
                "status": form_data.get(f"status_{student_id}", ""),
                "notes": form_data.get(f"notes_{student_id}", ""),
            }
        )
        for student_id in student_ids
    }


def validate_bulk_attendance(records):
    return {
        student_id: errors
        for student_id, data in records.items()
        if (errors := validate_attendance_data(data))
    }


def get_session_details(session_id, user_id):
    return _fetch_one(
        """
        SELECT ats.id, ats.session_date, ats.period_number, ats.status,
               TIME_FORMAT(ats.scheduled_start, '%H:%i') AS scheduled_start,
               TIME_FORMAT(ats.scheduled_end, '%H:%i') AS scheduled_end,
               s.subject_code, s.subject_name
        FROM attendance_sessions ats
        JOIN subjects s ON s.id=ats.subject_id
        JOIN faculty f ON f.id=ats.faculty_id
        WHERE ats.id=%s AND f.user_id=%s
        """,
        (session_id, user_id),
    )


def list_roster(session_id):
    return _fetch_all(
        """
        SELECT ar.id AS record_id, ar.student_id, ar.status, ar.first_entry,
               ar.last_exit, ar.notes, ar.marking_method,
               st.register_number, st.full_name
        FROM attendance_records ar
        JOIN students st ON st.id=ar.student_id
        WHERE ar.session_id=%s
        ORDER BY st.register_number, st.full_name
        """,
        (session_id,),
    )


def attendance_totals(session_id):
    rows = _fetch_all(
        "SELECT status, COUNT(*) AS total FROM attendance_records WHERE session_id=%s GROUP BY status",
        (session_id,),
    )
    totals = {status: 0 for status in MANUAL_STATUSES}
    for row in rows:
        totals[row["status"]] = row["total"]
    return totals


def update_record(session_id, student_id, user_id, data):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """SELECT ats.status FROM attendance_sessions ats
               JOIN faculty f ON f.id=ats.faculty_id
               WHERE ats.id=%s AND f.user_id=%s FOR UPDATE""",
            (session_id, user_id),
        )
        active_session = cursor.fetchone()
        if active_session is None:
            return "not_found"
        if active_session["status"] not in EDITABLE_SESSION_STATUSES:
            return "locked"
        cursor.execute(
            """UPDATE attendance_records
               SET status=%s, notes=%s, marking_method='MANUAL',
                   first_entry=CASE
                     WHEN %s IN ('PRESENT','LATE') THEN COALESCE(first_entry,NOW())
                     ELSE NULL END,
                   last_exit=CASE WHEN %s='LEFT_EARLY' THEN NOW() ELSE last_exit END
               WHERE session_id=%s AND student_id=%s""",
            (data["status"], data["notes"] or None, data["status"], data["status"], session_id, student_id),
        )
        if cursor.rowcount == 0:
            return "not_found"
        connection.commit()
        return "updated"
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close(); connection.close()


def update_records_bulk(session_id, user_id, records):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """SELECT ats.status FROM attendance_sessions ats
               JOIN faculty f ON f.id=ats.faculty_id
               WHERE ats.id=%s AND f.user_id=%s FOR UPDATE""",
            (session_id, user_id),
        )
        active_session = cursor.fetchone()
        if active_session is None:
            return "not_found"
        if active_session["status"] not in EDITABLE_SESSION_STATUSES:
            return "locked"

        cursor.execute(
            "SELECT student_id FROM attendance_records WHERE session_id=%s FOR UPDATE",
            (session_id,),
        )
        roster_ids = {row["student_id"] for row in cursor.fetchall()}
        if not roster_ids or set(records) != roster_ids:
            return "incomplete"

        query = """UPDATE attendance_records
                   SET status=%s, notes=%s, marking_method='MANUAL',
                       first_entry=CASE
                         WHEN %s IN ('PRESENT','LATE') THEN COALESCE(first_entry,NOW())
                         ELSE NULL END,
                       last_exit=CASE
                         WHEN %s='LEFT_EARLY' THEN COALESCE(last_exit,NOW())
                         WHEN %s<>'LEFT_EARLY' THEN NULL ELSE last_exit END
                   WHERE session_id=%s AND student_id=%s"""
        for student_id, data in records.items():
            cursor.execute(
                query,
                (
                    data["status"], data["notes"] or None, data["status"],
                    data["status"], data["status"], session_id, student_id,
                ),
            )
        connection.commit()
        return "updated"
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close(); connection.close()


def _fetch_all(query, params=()):
    connection=get_db_connection(); cursor=connection.cursor(dictionary=True)
    try: cursor.execute(query,params); return cursor.fetchall()
    finally: cursor.close(); connection.close()


def _fetch_one(query, params=()):
    connection=get_db_connection(); cursor=connection.cursor(dictionary=True)
    try: cursor.execute(query,params); return cursor.fetchone()
    finally: cursor.close(); connection.close()

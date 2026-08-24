from db import get_db_connection


REQUESTABLE_STATUSES = ("PRESENT", "ABSENT", "LATE", "LEFT_EARLY", "ON_DUTY", "MEDICAL")
REVIEW_DECISIONS = ("APPROVE", "REJECT")


def normalize_request_data(form_data):
    return {
        "attendance_record_id": _positive_int(form_data.get("attendance_record_id")),
        "requested_status": str(form_data.get("requested_status", "")).strip().upper(),
        "reason": " ".join(str(form_data.get("reason", "")).strip().split()),
    }


def validate_request_data(data):
    errors = {}
    if data["attendance_record_id"] is None:
        errors["attendance_record_id"] = "Select an attendance record."
    if data["requested_status"] not in REQUESTABLE_STATUSES:
        errors["requested_status"] = "Select a valid corrected status."
    if not data["reason"]:
        errors["reason"] = "Explain why this attendance should be corrected."
    elif len(data["reason"]) > 500:
        errors["reason"] = "Reason must contain no more than 500 characters."
    return errors


def normalize_review_data(form_data):
    return {
        "decision": str(form_data.get("decision", "")).strip().upper(),
        "comment": " ".join(str(form_data.get("comment", "")).strip().split()),
    }


def validate_review_data(data):
    errors = {}
    if data["decision"] not in REVIEW_DECISIONS:
        errors["decision"] = "Select Approve or Reject."
    if data["decision"] == "REJECT" and not data["comment"]:
        errors["comment"] = "Add a comment explaining the rejection."
    elif len(data["comment"]) > 500:
        errors["comment"] = "Comment must contain no more than 500 characters."
    return errors


def list_student_records(user_id):
    return _fetch_all(
        """SELECT ar.id AS attendance_record_id, ar.status AS current_status,
                  ats.session_date, ats.period_number,
                  TIME_FORMAT(ats.scheduled_start, '%H:%i') AS scheduled_start,
                  TIME_FORMAT(ats.scheduled_end, '%H:%i') AS scheduled_end,
                  s.subject_code, s.subject_name, f.full_name AS faculty_name,
                  cr.id AS request_id, cr.status AS request_status
           FROM students st
           JOIN attendance_records ar ON ar.student_id=st.id
           JOIN attendance_sessions ats ON ats.id=ar.session_id AND ats.status='CONFIRMED'
           JOIN subjects s ON s.id=ats.subject_id
           JOIN faculty f ON f.id=ats.faculty_id
           LEFT JOIN attendance_correction_requests cr ON cr.attendance_record_id=ar.id
           WHERE st.user_id=%s AND st.is_active=TRUE
           ORDER BY ats.session_date DESC, ats.period_number DESC""",
        (user_id,),
    )


def list_student_requests(user_id):
    return _fetch_all(
        """SELECT cr.id, cr.requested_status, cr.reason, cr.status,
                  cr.reviewer_comment, cr.reviewed_at, cr.created_at,
                  ar.status AS current_status, ats.session_date, ats.period_number,
                  s.subject_code, s.subject_name,
                  reviewer.full_name AS reviewer_name
           FROM attendance_correction_requests cr
           JOIN students st ON st.id=cr.student_id
           JOIN attendance_records ar ON ar.id=cr.attendance_record_id
           JOIN attendance_sessions ats ON ats.id=ar.session_id
           JOIN subjects s ON s.id=ats.subject_id
           LEFT JOIN users reviewer ON reviewer.id=cr.reviewed_by_user_id
           WHERE st.user_id=%s
           ORDER BY cr.created_at DESC""",
        (user_id,),
    )


def create_request(user_id, data):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """SELECT ar.id, ar.student_id
               FROM attendance_records ar
               JOIN attendance_sessions ats ON ats.id=ar.session_id
               JOIN students st ON st.id=ar.student_id
               WHERE ar.id=%s AND st.user_id=%s AND st.is_active=TRUE
                 AND ats.status='CONFIRMED' FOR UPDATE""",
            (data["attendance_record_id"], user_id),
        )
        record = cursor.fetchone()
        if record is None:
            connection.rollback()
            return "not_found"
        cursor.execute(
            "SELECT id FROM attendance_correction_requests WHERE attendance_record_id=%s",
            (record["id"],),
        )
        if cursor.fetchone() is not None:
            connection.rollback()
            return "duplicate"
        cursor.execute(
            """INSERT INTO attendance_correction_requests
               (attendance_record_id, student_id, requested_status, reason)
               VALUES (%s,%s,%s,%s)""",
            (record["id"], record["student_id"], data["requested_status"], data["reason"]),
        )
        connection.commit()
        return "created"
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def list_review_requests(user_id, role, status="PENDING"):
    role = str(role).upper()
    clauses = ["cr.status=%s"]
    params = [status]
    if role == "FACULTY":
        clauses.append("f.user_id=%s")
        params.append(user_id)
    elif role != "ADMIN":
        return []
    return _fetch_all(
        f"""SELECT cr.id, cr.requested_status, cr.reason, cr.status,
                   cr.reviewer_comment, cr.reviewed_at, cr.created_at,
                   ar.status AS current_status, st.register_number,
                   st.full_name AS student_name, ats.session_date, ats.period_number,
                   s.subject_code, s.subject_name, f.full_name AS faculty_name,
                   reviewer.full_name AS reviewer_name
            FROM attendance_correction_requests cr
            JOIN attendance_records ar ON ar.id=cr.attendance_record_id
            JOIN students st ON st.id=cr.student_id
            JOIN attendance_sessions ats ON ats.id=ar.session_id
            JOIN subjects s ON s.id=ats.subject_id
            JOIN faculty f ON f.id=ats.faculty_id
            LEFT JOIN users reviewer ON reviewer.id=cr.reviewed_by_user_id
            WHERE {' AND '.join(clauses)}
            ORDER BY cr.created_at DESC""",
        tuple(params),
    )


def review_request(request_id, reviewer_user_id, role, data):
    role = str(role).upper()
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """SELECT cr.id, cr.attendance_record_id, cr.requested_status, cr.reason,
                      cr.status, f.user_id AS faculty_user_id,
                      ats.session_date, ats.scheduled_start
               FROM attendance_correction_requests cr
               JOIN attendance_records ar ON ar.id=cr.attendance_record_id
               JOIN attendance_sessions ats ON ats.id=ar.session_id
               JOIN faculty f ON f.id=ats.faculty_id
               WHERE cr.id=%s FOR UPDATE""",
            (request_id,),
        )
        correction = cursor.fetchone()
        if correction is None:
            connection.rollback()
            return "not_found"
        if role == "FACULTY" and correction["faculty_user_id"] != reviewer_user_id:
            connection.rollback()
            return "forbidden"
        if role not in ("ADMIN", "FACULTY"):
            connection.rollback()
            return "forbidden"
        if correction["status"] != "PENDING":
            connection.rollback()
            return "already_reviewed"

        decision_status = "APPROVED" if data["decision"] == "APPROVE" else "REJECTED"
        if decision_status == "APPROVED":
            requested = correction["requested_status"]
            cursor.execute(
                """UPDATE attendance_records
                   SET status=%s, marking_method='ADMIN_CORRECTION', teacher_override=TRUE,
                       notes=%s,
                       first_entry=CASE
                         WHEN %s IN ('PRESENT','LATE','LEFT_EARLY')
                           THEN COALESCE(first_entry,TIMESTAMP(%s,%s))
                         ELSE NULL END,
                       last_exit=CASE WHEN %s IN ('ABSENT','ON_DUTY','MEDICAL') THEN NULL ELSE last_exit END,
                       total_present_seconds=CASE WHEN %s IN ('ABSENT','ON_DUTY','MEDICAL') THEN 0 ELSE total_present_seconds END
                   WHERE id=%s""",
                (
                    requested, data["comment"] or correction["reason"], requested,
                    correction["session_date"], correction["scheduled_start"],
                    requested, requested, correction["attendance_record_id"],
                ),
            )
        cursor.execute(
            """UPDATE attendance_correction_requests
               SET status=%s, reviewed_by_user_id=%s, reviewer_comment=%s, reviewed_at=NOW()
               WHERE id=%s""",
            (decision_status, reviewer_user_id, data["comment"] or None, request_id),
        )
        connection.commit()
        return decision_status.lower()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def _positive_int(value):
    try:
        value = int(str(value).strip())
        return value if value > 0 else None
    except (TypeError, ValueError):
        return None


def _fetch_all(query, params=()):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

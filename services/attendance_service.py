import json
from datetime import datetime, timedelta

from db import get_db_connection
from services import face_service


MANUAL_STATUSES = ("PRESENT", "ABSENT", "LATE", "LEFT_EARLY", "NOT_MARKED")
EDITABLE_SESSION_STATUSES = ("ACTIVE", "REVIEW")
FACE_MATCH_AMBIGUITY_MARGIN = 0.05
FACE_ATTENDANCE_MODES = ("ENTRY", "EXIT")
LATE_AFTER_MINUTES = 10
EARLY_EXIT_BEFORE_MINUTES = 5


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
               ar.last_exit, ar.total_present_seconds, ar.notes, ar.marking_method,
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


def recognize_and_mark(session_id, user_id, probe_embedding, mode="ENTRY", now=None):
    """Match one face and atomically record its entry or exit event."""
    mode = str(mode).strip().upper()
    if mode not in FACE_ATTENDANCE_MODES:
        return {"result": "invalid_mode"}

    event_time = now or datetime.now()
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """SELECT ats.status,
                      TIMESTAMP(ats.session_date, ats.scheduled_start) AS scheduled_start_at,
                      TIMESTAMP(ats.session_date, ats.scheduled_end) AS scheduled_end_at
               FROM attendance_sessions ats
               JOIN faculty f ON f.id=ats.faculty_id
               WHERE ats.id=%s AND f.user_id=%s FOR UPDATE""",
            (session_id, user_id),
        )
        active_session = cursor.fetchone()
        if active_session is None:
            connection.rollback()
            return {"result": "not_found"}
        if active_session["status"] != "ACTIVE":
            connection.rollback()
            return {"result": "locked"}

        cursor.execute(
            """SELECT ar.student_id, ar.status, ar.first_entry, ar.last_exit,
                      ar.total_present_seconds,
                      st.register_number, st.full_name, fe.embedding_data
               FROM attendance_records ar
               JOIN students st ON st.id=ar.student_id AND st.is_active=TRUE
               JOIN face_embeddings fe ON fe.student_id=st.id AND fe.model_name=%s
               WHERE ar.session_id=%s
               FOR UPDATE""",
            (face_service.MODEL_NAME, session_id),
        )
        candidates = cursor.fetchall()
        if not candidates:
            connection.rollback()
            return {"result": "no_registered"}

        ranked = [
            (
                face_service.cosine_similarity(
                    probe_embedding,
                    _deserialize_embedding(candidate["embedding_data"]),
                ),
                candidate,
            )
            for candidate in candidates
        ]
        ranked.sort(key=lambda item: item[0])
        best_score, matched = ranked[-1]
        if best_score < face_service.COSINE_MATCH_THRESHOLD:
            connection.rollback()
            return {"result": "unknown", "score": round(best_score, 5)}
        if len(ranked) > 1 and best_score - ranked[-2][0] < FACE_MATCH_AMBIGUITY_MARGIN:
            connection.rollback()
            return {"result": "ambiguous", "score": round(best_score, 5)}

        student = {
            "id": matched["student_id"],
            "register_number": matched["register_number"],
            "full_name": matched["full_name"],
        }
        score = round(best_score, 5)
        if mode == "ENTRY":
            if matched["first_entry"] is not None:
                connection.rollback()
                return {
                    "result": "duplicate_entry", "student": student, "score": score,
                }
            attendance_status = _entry_status(
                event_time, active_session.get("scheduled_start_at")
            )
            cursor.execute(
                """UPDATE attendance_records
                   SET status=%s, first_entry=%s, last_exit=NULL,
                       total_present_seconds=0, marking_method='FACE',
                       teacher_override=FALSE, notes=NULL
                   WHERE session_id=%s AND student_id=%s""",
                (attendance_status, event_time, session_id, matched["student_id"]),
            )
            result_name = "entry_recorded"
            duration_seconds = 0
        else:
            if matched["first_entry"] is None:
                connection.rollback()
                return {
                    "result": "entry_required", "student": student, "score": score,
                }
            if matched["last_exit"] is not None:
                connection.rollback()
                return {
                    "result": "duplicate_exit", "student": student, "score": score,
                    "duration_seconds": matched.get("total_present_seconds") or 0,
                }
            duration_seconds = _presence_seconds(matched["first_entry"], event_time)
            attendance_status = _exit_status(
                matched["status"], event_time, active_session.get("scheduled_end_at")
            )
            cursor.execute(
                """UPDATE attendance_records
                   SET status=%s, last_exit=%s, total_present_seconds=%s,
                       marking_method='FACE', teacher_override=FALSE, notes=NULL
                   WHERE session_id=%s AND student_id=%s""",
                (
                    attendance_status, event_time, duration_seconds,
                    session_id, matched["student_id"],
                ),
            )
            result_name = "exit_recorded"

        cursor.execute(
            """INSERT INTO attendance_events
               (session_id, student_id, event_type, event_time, similarity_score, source)
               VALUES (%s,%s,%s,%s,%s,'FACE')""",
            (session_id, matched["student_id"], mode, event_time, score),
        )
        connection.commit()
        return {
            "result": result_name,
            "event_type": mode,
            "student": student,
            "score": score,
            "status": attendance_status,
            "duration_seconds": duration_seconds,
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close(); connection.close()


def _deserialize_embedding(value):
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, list):
        raise ValueError("Stored face embedding is invalid.")
    return value


def _entry_status(event_time, scheduled_start_at):
    scheduled_start_at = _as_datetime(scheduled_start_at)
    if scheduled_start_at and event_time > scheduled_start_at + timedelta(minutes=LATE_AFTER_MINUTES):
        return "LATE"
    return "PRESENT"


def _exit_status(current_status, event_time, scheduled_end_at):
    scheduled_end_at = _as_datetime(scheduled_end_at)
    if scheduled_end_at and event_time < scheduled_end_at - timedelta(minutes=EARLY_EXIT_BEFORE_MINUTES):
        return "LEFT_EARLY"
    return current_status if current_status in ("PRESENT", "LATE") else "PRESENT"


def _presence_seconds(first_entry, exit_time):
    first_entry = _as_datetime(first_entry)
    if first_entry is None:
        return 0
    return max(0, int((exit_time - first_entry).total_seconds()))


def _as_datetime(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _fetch_all(query, params=()):
    connection=get_db_connection(); cursor=connection.cursor(dictionary=True)
    try: cursor.execute(query,params); return cursor.fetchall()
    finally: cursor.close(); connection.close()


def _fetch_one(query, params=()):
    connection=get_db_connection(); cursor=connection.cursor(dictionary=True)
    try: cursor.execute(query,params); return cursor.fetchone()
    finally: cursor.close(); connection.close()

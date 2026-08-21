from collections import OrderedDict
from datetime import datetime

from db import get_db_connection


ATTENDED_STATUSES = {"PRESENT", "LATE", "LEFT_EARLY", "ON_DUTY", "MEDICAL"}
LOW_ATTENDANCE_THRESHOLD = 75.0


def normalize_filters(values):
    filters = {"subject_id": None, "month": "", "date": ""}
    errors = {}

    subject_id = str(values.get("subject_id", "")).strip()
    if subject_id:
        try:
            filters["subject_id"] = int(subject_id)
            if filters["subject_id"] < 1:
                raise ValueError
        except ValueError:
            errors["subject_id"] = "Select a valid subject."

    month = str(values.get("month", "")).strip()
    if month:
        try:
            datetime.strptime(month, "%Y-%m")
            filters["month"] = month
        except ValueError:
            errors["month"] = "Select a valid month."

    exact_date = str(values.get("date", "")).strip()
    if exact_date:
        try:
            datetime.strptime(exact_date, "%Y-%m-%d")
            filters["date"] = exact_date
        except ValueError:
            errors["date"] = "Select a valid date."

    return filters, errors


def get_student_report(user_id, filters=None):
    filters = filters or {"subject_id": None, "month": "", "date": ""}
    student = _fetch_one(
        """SELECT st.id, st.register_number, st.full_name, st.semester_id,
                  c.code AS course_code, c.name AS course_name,
                  sem.semester_number, sem.section, sem.academic_year
           FROM students st
           JOIN courses c ON c.id=st.course_id
           JOIN semesters sem ON sem.id=st.semester_id
           WHERE st.user_id=%s AND st.is_active=TRUE""",
        (user_id,),
    )
    if student is None:
        return None

    clauses = ["ar.student_id=%s", "ats.semester_id=%s", "ats.status='CONFIRMED'"]
    params = [student["id"], student["semester_id"]]
    if filters.get("subject_id"):
        clauses.append("ats.subject_id=%s")
        params.append(filters["subject_id"])
    if filters.get("month"):
        clauses.append("DATE_FORMAT(ats.session_date, '%Y-%m')=%s")
        params.append(filters["month"])
    if filters.get("date"):
        clauses.append("ats.session_date=%s")
        params.append(filters["date"])

    history = _fetch_all(
        f"""SELECT ats.id AS session_id, ats.session_date, ats.period_number,
                   TIME_FORMAT(ats.scheduled_start, '%H:%i') AS scheduled_start,
                   TIME_FORMAT(ats.scheduled_end, '%H:%i') AS scheduled_end,
                   s.id AS subject_id, s.subject_code, s.subject_name,
                   f.full_name AS faculty_name,
                   ar.status, ar.first_entry, ar.last_exit,
                   ar.total_present_seconds, ar.marking_method
            FROM attendance_records ar
            JOIN attendance_sessions ats ON ats.id=ar.session_id
            JOIN subjects s ON s.id=ats.subject_id
            JOIN faculty f ON f.id=ats.faculty_id
            WHERE {' AND '.join(clauses)}
            ORDER BY ats.session_date DESC, ats.period_number DESC""",
        tuple(params),
    )
    subjects = _fetch_all(
        """SELECT id, subject_code, subject_name FROM subjects
           WHERE semester_id=%s AND is_active=TRUE
           ORDER BY subject_code""",
        (student["semester_id"],),
    )
    return build_report(student, history, subjects)


def build_report(student, history, available_subjects=None):
    totals = _empty_totals()
    grouped = OrderedDict()
    normalized_history = []

    for raw_row in history:
        row = dict(raw_row)
        row["total_present_seconds"] = int(row.get("total_present_seconds") or 0)
        row["duration_label"] = format_duration(row["total_present_seconds"])
        normalized_history.append(row)
        _count_status(totals, row.get("status"))

        subject_id = row["subject_id"]
        if subject_id not in grouped:
            grouped[subject_id] = {
                "subject_id": subject_id,
                "subject_code": row["subject_code"],
                "subject_name": row["subject_name"],
                **_empty_totals(),
            }
        _count_status(grouped[subject_id], row.get("status"))

    _finish_totals(totals)
    subject_summaries = []
    for subject in grouped.values():
        _finish_totals(subject)
        subject["low_attendance"] = subject["percentage"] < LOW_ATTENDANCE_THRESHOLD
        subject_summaries.append(subject)

    return {
        "student": student,
        "summary": totals,
        "subjects": subject_summaries,
        "history": normalized_history,
        "available_subjects": available_subjects or [],
        "threshold": LOW_ATTENDANCE_THRESHOLD,
        "low_attendance": bool(totals["total"] and totals["percentage"] < LOW_ATTENDANCE_THRESHOLD),
    }


def format_duration(seconds):
    seconds = max(0, int(seconds or 0))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m {seconds}s"


def _empty_totals():
    return {
        "total": 0, "attended": 0, "present": 0, "absent": 0,
        "late": 0, "left_early": 0, "on_duty": 0, "medical": 0,
    }


def _count_status(totals, status):
    if status in (None, "NOT_MARKED", "NOT_CONDUCTED"):
        return
    totals["total"] += 1
    if status in ATTENDED_STATUSES:
        totals["attended"] += 1
    key = str(status).lower()
    if key in totals:
        totals[key] += 1


def _finish_totals(totals):
    totals["percentage"] = round(
        totals["attended"] * 100 / totals["total"], 1
    ) if totals["total"] else 0.0


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

from collections import OrderedDict
from calendar import month_name
from datetime import datetime

from db import get_db_connection


ATTENDED_STATUSES = {"PRESENT", "LATE", "LEFT_EARLY", "ON_DUTY", "MEDICAL"}
LOW_ATTENDANCE_THRESHOLD = 75.0


def get_month_options(filters=None, current_year=None):
    filters = filters or {}
    selected_period = filters.get("month") or str(filters.get("date", ""))[:7]
    try:
        year = int(selected_period[:4]) if selected_period else int(current_year or datetime.now().year)
    except (TypeError, ValueError):
        year = int(current_year or datetime.now().year)
    return [
        {"value": f"{year}-{month:02d}", "label": month_name[month]}
        for month in range(1, 13)
    ]


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


def normalize_student_filters(values):
    filters, errors = normalize_filters(values)
    filters["semester"] = None
    semester = str(values.get("semester", "")).strip()
    if semester:
        try:
            filters["semester"] = int(semester)
            if filters["semester"] not in range(1, 5):
                raise ValueError
        except ValueError:
            errors["semester"] = "Select a valid semester."
    return filters, errors


def normalize_cohort_filters(values):
    filters, errors = normalize_filters(values)
    filters["student_id"] = None
    filters["semester_id"] = None
    student_id = str(values.get("student_id", "")).strip()
    if student_id:
        try:
            filters["student_id"] = int(student_id)
            if filters["student_id"] < 1:
                raise ValueError
        except ValueError:
            errors["student_id"] = "Select a valid student."
    semester_id = str(values.get("semester_id", "")).strip()
    if semester_id:
        try:
            filters["semester_id"] = int(semester_id)
            if filters["semester_id"] < 1:
                raise ValueError
        except ValueError:
            errors["semester_id"] = "Select a valid semester."
    return filters, errors


def get_student_report(user_id, filters=None):
    filters = filters or {"subject_id": None, "month": "", "date": "", "semester": None}
    student = _fetch_one(
        """SELECT st.id, st.register_number, st.full_name, st.course_id, st.semester_id,
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

    selected_semester = filters.get("semester") or student["semester_number"]
    target_semester = {"id": student["semester_id"]}
    if selected_semester != student["semester_number"]:
        target_semester = _fetch_one(
            """SELECT id FROM semesters
               WHERE course_id=%s AND semester_number=%s
               ORDER BY academic_year DESC, section LIMIT 1""",
            (student["course_id"], selected_semester),
        )
    student = dict(student)
    student["semester_number"] = selected_semester
    if target_semester is None:
        return build_report(student, [], [])

    clauses = ["ar.student_id=%s", "ats.semester_id=%s", "ats.status='CONFIRMED'"]
    params = [student["id"], target_semester["id"]]
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
        (target_semester["id"],),
    )
    return build_report(student, history, subjects)


def get_cohort_report(user_id, role, filters=None):
    filters = filters or {
        "student_id": None, "subject_id": None, "month": "", "date": "",
        "semester_id": None,
    }
    role = str(role).upper()
    faculty = None
    scope_clause = ""
    scope_params = []
    if role == "FACULTY":
        faculty = _fetch_one(
            "SELECT id, employee_code, full_name FROM faculty WHERE user_id=%s AND is_active=TRUE",
            (user_id,),
        )
        if faculty is None:
            return None
        scope_clause = " AND ats.faculty_id=%s"
        scope_params.append(faculty["id"])
    elif role != "ADMIN":
        return None

    clauses = ["ats.status='CONFIRMED'"]
    params = []
    if filters.get("semester_id"):
        clauses.append("ats.semester_id=%s")
        params.append(filters["semester_id"])
    if filters.get("student_id"):
        clauses.append("ar.student_id=%s")
        params.append(filters["student_id"])
    if filters.get("subject_id"):
        clauses.append("ats.subject_id=%s")
        params.append(filters["subject_id"])
    if filters.get("month"):
        clauses.append("DATE_FORMAT(ats.session_date, '%Y-%m')=%s")
        params.append(filters["month"])
    if filters.get("date"):
        clauses.append("ats.session_date=%s")
        params.append(filters["date"])
    params.extend(scope_params)

    history = _fetch_all(
        f"""SELECT ar.student_id, st.register_number, st.full_name AS student_name,
                   ats.session_date, ats.period_number,
                   TIME_FORMAT(ats.scheduled_start, '%H:%i') AS scheduled_start,
                   TIME_FORMAT(ats.scheduled_end, '%H:%i') AS scheduled_end,
                   s.id AS subject_id, s.subject_code, s.subject_name,
                   f.full_name AS faculty_name, ar.status, ar.first_entry, ar.last_exit,
                   ar.total_present_seconds, ar.marking_method
            FROM attendance_records ar
            JOIN students st ON st.id=ar.student_id
            JOIN attendance_sessions ats ON ats.id=ar.session_id
            JOIN subjects s ON s.id=ats.subject_id
            JOIN faculty f ON f.id=ats.faculty_id
            WHERE {' AND '.join(clauses)}{scope_clause}
            ORDER BY ats.session_date DESC, ats.period_number DESC, st.full_name""",
        tuple(params),
    )

    if faculty:
        subjects = _fetch_all(
            """SELECT DISTINCT s.id, s.subject_code, s.subject_name
               FROM subjects s JOIN faculty_subject_assignments a ON a.subject_id=s.id
               WHERE a.faculty_id=%s AND s.is_active=TRUE ORDER BY s.subject_code""",
            (faculty["id"],),
        )
    else:
        subject_clauses = ["is_active=TRUE"]
        subject_params = []
        if filters.get("semester_id"):
            subject_clauses.append("semester_id=%s")
            subject_params.append(filters["semester_id"])
        subjects = _fetch_all(
            f"""SELECT id, subject_code, subject_name FROM subjects
                WHERE {' AND '.join(subject_clauses)} ORDER BY subject_code""",
            tuple(subject_params),
        )
    student_scope = scope_clause
    student_params = list(scope_params)
    if filters.get("semester_id"):
        student_scope += " AND ats.semester_id=%s"
        student_params.append(filters["semester_id"])
    students = _fetch_all(
        f"""SELECT DISTINCT st.id, st.register_number, st.full_name
            FROM students st
            JOIN attendance_records ar ON ar.student_id=st.id
            JOIN attendance_sessions ats ON ats.id=ar.session_id
            WHERE st.is_active=TRUE{student_scope}
            ORDER BY st.full_name, st.register_number""",
        tuple(student_params),
    )
    return build_cohort_report(history, students, subjects, faculty)


def build_cohort_report(history, available_students=None, available_subjects=None, faculty=None):
    totals = _empty_totals()
    grouped = OrderedDict()
    normalized_history = []
    for raw_row in history:
        row = dict(raw_row)
        row["total_present_seconds"] = int(row.get("total_present_seconds") or 0)
        row["duration_label"] = format_duration(row["total_present_seconds"])
        normalized_history.append(row)
        _count_status(totals, row.get("status"))
        student_id = row["student_id"]
        if student_id not in grouped:
            grouped[student_id] = {
                "student_id": student_id,
                "register_number": row["register_number"],
                "student_name": row["student_name"],
                **_empty_totals(),
            }
        _count_status(grouped[student_id], row.get("status"))

    _finish_totals(totals)
    students = []
    for student in grouped.values():
        _finish_totals(student)
        student["low_attendance"] = student["percentage"] < LOW_ATTENDANCE_THRESHOLD
        students.append(student)
    students.sort(key=lambda row: (not row["low_attendance"], row["student_name"]))
    return {
        "summary": totals,
        "students": students,
        "history": normalized_history,
        "available_students": available_students or [],
        "available_subjects": available_subjects or [],
        "faculty": faculty,
        "threshold": LOW_ATTENDANCE_THRESHOLD,
        "low_attendance_count": sum(1 for row in students if row["low_attendance"]),
    }


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

    months = _build_month_summaries(normalized_history)
    dates = _build_date_groups(normalized_history)

    return {
        "student": student,
        "summary": totals,
        "subjects": subject_summaries,
        "history": normalized_history,
        "months": months,
        "dates": dates,
        "available_subjects": available_subjects or [],
        "threshold": LOW_ATTENDANCE_THRESHOLD,
        "low_attendance": bool(totals["total"] and totals["percentage"] < LOW_ATTENDANCE_THRESHOLD),
    }


def _build_month_summaries(history):
    grouped = OrderedDict()
    for row in history:
        session_date = row["session_date"]
        month_key = session_date.strftime("%Y-%m")
        if month_key not in grouped:
            grouped[month_key] = {
                "value": month_key,
                "year": session_date.year,
                "name": month_name[session_date.month],
                "subjects": OrderedDict(),
                **_empty_totals(),
            }
        month = grouped[month_key]
        _count_status(month, row.get("status"))
        subject_id = row["subject_id"]
        if subject_id not in month["subjects"]:
            month["subjects"][subject_id] = {
                "subject_code": row["subject_code"],
                "subject_name": row["subject_name"],
                **_empty_totals(),
            }
        _count_status(month["subjects"][subject_id], row.get("status"))

    summaries = []
    for month in grouped.values():
        _finish_totals(month)
        subject_summaries = []
        for subject in month["subjects"].values():
            _finish_totals(subject)
            subject_summaries.append(subject)
        month["subjects"] = subject_summaries
        summaries.append(month)
    return summaries


def _build_date_groups(history):
    grouped = OrderedDict()
    for row in history:
        session_date = row["session_date"]
        key = session_date.isoformat()
        if key not in grouped:
            grouped[key] = {
                "value": key,
                "label": session_date.strftime("%d %B %Y"),
                "rows": [],
            }
        grouped[key]["rows"].append(row)
    return list(grouped.values())


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

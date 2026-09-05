from datetime import datetime

from db import get_db_connection


DAYS = {1: "Monday", 2: "Tuesday", 3: "Wednesday", 4: "Thursday", 5: "Friday", 6: "Saturday"}


def normalize_period_data(form_data):
    data = {}
    for field in ("assignment_id", "day_of_week", "period_number"):
        try:
            data[field] = int(form_data.get(field, ""))
        except (TypeError, ValueError):
            data[field] = None
    data["start_time"] = form_data.get("start_time", "").strip()
    data["end_time"] = form_data.get("end_time", "").strip()
    data["activity_name"] = " ".join(form_data.get("activity_name", "").strip().split())
    return data


def validate_period_data(data):
    errors = {}
    if not data["assignment_id"] and not data["activity_name"]:
        errors["assignment_id"] = "Select a faculty assignment or enter an unassigned activity."
    if data["assignment_id"] and data["activity_name"]:
        errors["activity_name"] = "Choose an assignment or an unassigned activity, not both."
    if data["activity_name"] and len(data["activity_name"]) > 160:
        errors["activity_name"] = "Activity name is too long."
    if data["day_of_week"] not in DAYS:
        errors["day_of_week"] = "Select a day from Monday to Saturday."
    if not data["period_number"] or not 1 <= data["period_number"] <= 20:
        errors["period_number"] = "Enter a period number between 1 and 20."

    start = _parse_time(data["start_time"])
    end = _parse_time(data["end_time"])
    if start is None:
        errors["start_time"] = "Enter a valid start time."
    if end is None:
        errors["end_time"] = "Enter a valid end time."
    if start and end and start >= end:
        errors["end_time"] = "End time must be later than start time."
    return errors


def get_assignment_options(semester_id):
    return _fetch_all(
        """
        SELECT a.id, s.subject_code, s.subject_name, f.employee_code, f.full_name
        FROM faculty_subject_assignments a
        JOIN subjects s ON s.id = a.subject_id
        JOIN faculty f ON f.id = a.faculty_id
        WHERE s.semester_id=%s
          AND s.is_active = TRUE AND f.is_active = TRUE
        ORDER BY s.subject_code, f.full_name
        """, (semester_id,)
    )


def get_assignment(assignment_id, semester_id):
    return _fetch_one(
        """
        SELECT a.id, a.subject_id, a.faculty_id, s.semester_id
        FROM faculty_subject_assignments a
        JOIN subjects s ON s.id = a.subject_id
        JOIN faculty f ON f.id = a.faculty_id
        WHERE a.id=%s AND s.semester_id=%s
          AND s.is_active = TRUE AND f.is_active = TRUE
        """,
        (assignment_id,semester_id),
    )


def list_periods(semester_id):
    return _fetch_all(
        """
        SELECT tp.id, tp.day_of_week, tp.period_number,
               TIME_FORMAT(tp.start_time, '%H:%i') AS start_time,
               TIME_FORMAT(tp.end_time, '%H:%i') AS end_time,
               s.subject_code, COALESCE(tp.activity_name, s.subject_name) AS subject_name,
               f.employee_code, COALESCE(f.full_name, 'Unassigned') AS full_name,
               tp.activity_name,
               a.id AS assignment_id
        FROM timetable_periods tp
        LEFT JOIN subjects s ON s.id = tp.subject_id
        LEFT JOIN faculty f ON f.id = tp.faculty_id
        LEFT JOIN faculty_subject_assignments a
          ON a.subject_id = tp.subject_id AND a.faculty_id = tp.faculty_id
        WHERE tp.semester_id=%s
        ORDER BY tp.day_of_week, tp.period_number, tp.start_time
        """, (semester_id,)
    )


def get_period(period_id):
    return _fetch_one(
        """
        SELECT tp.id, tp.semester_id, tp.day_of_week, tp.period_number,
               TIME_FORMAT(tp.start_time, '%H:%i') AS start_time,
               TIME_FORMAT(tp.end_time, '%H:%i') AS end_time,
               a.id AS assignment_id, tp.activity_name
        FROM timetable_periods tp
        LEFT JOIN faculty_subject_assignments a
          ON a.subject_id = tp.subject_id AND a.faculty_id = tp.faculty_id
        WHERE tp.id = %s
        """,
        (period_id,),
    )


def find_conflict(data, assignment, exclude_period_id=None):
    exclusion = " AND tp.id <> %s" if exclude_period_id else ""
    base_params = [data["day_of_week"], data["end_time"], data["start_time"]]
    if exclude_period_id:
        base_params.append(exclude_period_id)

    semester = _fetch_one(
        f"""
        SELECT tp.id FROM timetable_periods tp
        WHERE tp.day_of_week = %s AND tp.start_time < %s AND tp.end_time > %s
          AND tp.semester_id = %s{exclusion} LIMIT 1
        """,
        tuple(base_params[:3] + [assignment["semester_id"]] + base_params[3:]),
    )
    if semester:
        return "semester"

    if assignment.get("faculty_id") is None:
        return None
    faculty = _fetch_one(
        f"""
        SELECT tp.id FROM timetable_periods tp
        WHERE tp.day_of_week = %s AND tp.start_time < %s AND tp.end_time > %s
          AND tp.faculty_id = %s{exclusion} LIMIT 1
        """,
        tuple(base_params[:3] + [assignment["faculty_id"]] + base_params[3:]),
    )
    return "faculty" if faculty else None


def create_period(data, assignment):
    return _write_period(None, data, assignment)


def update_period(period_id, data, assignment):
    return _write_period(period_id, data, assignment)


def _write_period(period_id, data, assignment):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        values = (assignment["semester_id"], assignment.get("subject_id"), assignment.get("faculty_id"),
                  data.get("activity_name") or None, data["day_of_week"], data["period_number"],
                  data["start_time"], data["end_time"])
        if period_id is None:
            cursor.execute(
                """INSERT INTO timetable_periods
                   (semester_id, subject_id, faculty_id, activity_name, day_of_week, period_number, start_time, end_time)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""", values,
            )
            result = cursor.lastrowid
        else:
            cursor.execute(
                """UPDATE timetable_periods SET semester_id=%s, subject_id=%s, faculty_id=%s,
                   activity_name=%s, day_of_week=%s, period_number=%s, start_time=%s, end_time=%s WHERE id=%s""",
                values + (period_id,),
            )
            result = cursor.rowcount > 0
        connection.commit()
        return result
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def delete_period(period_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("DELETE FROM timetable_periods WHERE id = %s", (period_id,))
        connection.commit()
        return cursor.rowcount > 0
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def _parse_time(value):
    try:
        return datetime.strptime(value, "%H:%M").time()
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


def _fetch_one(query, params=()):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        return cursor.fetchone()
    finally:
        cursor.close()
        connection.close()

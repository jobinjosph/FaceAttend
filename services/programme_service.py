import re

from db import get_db_connection


CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9_-]{1,29}$")
ACADEMIC_YEAR_PATTERN = re.compile(r"^\d{4}-\d{2}$")


def normalize_programme_data(values):
    try:
        total_semesters = int(values.get("total_semesters", ""))
    except (TypeError, ValueError):
        total_semesters = None
    return {
        "code": "".join(str(values.get("code", "")).upper().split()),
        "name": " ".join(str(values.get("name", "")).strip().split()),
        "total_semesters": total_semesters,
    }


def validate_programme_data(data):
    errors = {}
    if not data["code"]:
        errors["code"] = "Programme code is required."
    elif not CODE_PATTERN.fullmatch(data["code"]):
        errors["code"] = "Use 2–30 letters, numbers, hyphens or underscores."
    if not data["name"]:
        errors["name"] = "Programme name is required."
    elif len(data["name"]) > 150:
        errors["name"] = "Programme name is too long."
    if data["total_semesters"] is None or not 1 <= data["total_semesters"] <= 12:
        errors["total_semesters"] = "Enter a number from 1 to 12."
    return errors


def list_programmes():
    return _fetch_all(
        """SELECT c.id, c.code, c.name, c.total_semesters, c.is_active,
                  COUNT(DISTINCT sem.id) AS cohort_count,
                  COUNT(DISTINCT st.id) AS student_count
           FROM courses c
           LEFT JOIN semesters sem ON sem.course_id=c.id
           LEFT JOIN students st ON st.course_id=c.id
           GROUP BY c.id, c.code, c.name, c.total_semesters, c.is_active
           ORDER BY c.is_active DESC, c.name, c.code"""
    )


def get_programme(programme_id):
    return _fetch_one(
        """SELECT c.id, c.code, c.name, c.total_semesters, c.is_active,
                  COALESCE(MAX(sem.semester_number), 0) AS highest_configured_semester
           FROM courses c LEFT JOIN semesters sem ON sem.course_id=c.id
           WHERE c.id=%s
           GROUP BY c.id, c.code, c.name, c.total_semesters, c.is_active""",
        (programme_id,),
    )


def get_programme_impact(programme_id):
    return _fetch_one(
        """SELECT c.id, c.code,
                  (SELECT COUNT(*) FROM semesters sem WHERE sem.course_id=c.id) AS cohorts,
                  (SELECT COUNT(*) FROM students st WHERE st.course_id=c.id) AS students,
                  (SELECT COUNT(*) FROM subjects s JOIN semesters sem ON sem.id=s.semester_id
                   WHERE sem.course_id=c.id) AS subjects,
                  (SELECT COUNT(*) FROM timetable_periods tp JOIN semesters sem ON sem.id=tp.semester_id
                   WHERE sem.course_id=c.id) AS timetable_periods,
                  (SELECT COUNT(*) FROM attendance_sessions ats JOIN semesters sem ON sem.id=ats.semester_id
                   WHERE sem.course_id=c.id) AS attendance_sessions,
                  (SELECT COUNT(*) FROM attendance_records ar
                   JOIN attendance_sessions ats ON ats.id=ar.session_id
                   JOIN semesters sem ON sem.id=ats.semester_id
                   WHERE sem.course_id=c.id) AS attendance_records
           FROM courses c WHERE c.id=%s""",
        (programme_id,),
    )


def create_programme(data):
    return _write(
        "INSERT INTO courses (code, name, total_semesters, is_active) VALUES (%s,%s,%s,TRUE)",
        (data["code"], data["name"], data["total_semesters"]),
    )


def update_programme(programme_id, data):
    return _write(
        "UPDATE courses SET code=%s, name=%s, total_semesters=%s WHERE id=%s",
        (data["code"], data["name"], data["total_semesters"], programme_id),
    )


def set_programme_active(programme_id, is_active):
    return _write("UPDATE courses SET is_active=%s WHERE id=%s", (bool(is_active), programme_id))


def delete_unused_programme(programme_id):
    impact = get_programme_impact(programme_id)
    if impact is None:
        return "missing"
    if any(int(impact[field] or 0) for field in (
        "cohorts", "students", "subjects", "timetable_periods",
        "attendance_sessions", "attendance_records",
    )):
        return "in_use"
    _write("DELETE FROM courses WHERE id=%s", (programme_id,))
    return "deleted"


def normalize_cohort_data(values):
    try:
        semester_number = int(values.get("semester_number", ""))
    except (TypeError, ValueError):
        semester_number = None
    return {
        "semester_number": semester_number,
        "section": "".join(str(values.get("section", "")).upper().split()),
        "academic_year": str(values.get("academic_year", "")).strip(),
    }


def validate_cohort_data(data, programme):
    errors = {}
    if data["semester_number"] is None or not 1 <= data["semester_number"] <= int(programme["total_semesters"]):
        errors["semester_number"] = f"Select a semester from 1 to {programme['total_semesters']}."
    if not data["section"]:
        errors["section"] = "Section is required."
    elif len(data["section"]) > 20:
        errors["section"] = "Section is too long."
    if not ACADEMIC_YEAR_PATTERN.fullmatch(data["academic_year"]):
        errors["academic_year"] = "Use the academic-year format 2026-27."
    return errors


def list_cohorts(programme_id):
    return _fetch_all(
        """SELECT sem.id, sem.semester_number, sem.section, sem.academic_year,
                  sem.is_active, COUNT(DISTINCT st.id) AS student_count,
                  COUNT(DISTINCT s.id) AS subject_count,
                  COUNT(DISTINCT tp.id) AS timetable_count,
                  COUNT(DISTINCT ats.id) AS session_count
           FROM semesters sem
           LEFT JOIN students st ON st.semester_id=sem.id
           LEFT JOIN subjects s ON s.semester_id=sem.id
           LEFT JOIN timetable_periods tp ON tp.semester_id=sem.id
           LEFT JOIN attendance_sessions ats ON ats.semester_id=sem.id
           WHERE sem.course_id=%s
           GROUP BY sem.id, sem.semester_number, sem.section, sem.academic_year, sem.is_active
           ORDER BY sem.academic_year DESC, sem.semester_number, sem.section""",
        (programme_id,),
    )


def get_cohort(programme_id, cohort_id):
    return _fetch_one(
        """SELECT sem.id, sem.course_id, sem.semester_number, sem.section,
                  sem.academic_year, sem.is_active
           FROM semesters sem WHERE sem.course_id=%s AND sem.id=%s""",
        (programme_id, cohort_id),
    )


def get_cohort_impact(cohort_id):
    return _fetch_one(
        """SELECT sem.id,
                  (SELECT COUNT(*) FROM students st WHERE st.semester_id=sem.id) AS students,
                  (SELECT COUNT(*) FROM subjects s WHERE s.semester_id=sem.id) AS subjects,
                  (SELECT COUNT(*) FROM timetable_periods tp WHERE tp.semester_id=sem.id) AS timetable_periods,
                  (SELECT COUNT(*) FROM attendance_sessions ats WHERE ats.semester_id=sem.id) AS attendance_sessions,
                  (SELECT COUNT(*) FROM attendance_records ar
                   JOIN attendance_sessions ats ON ats.id=ar.session_id
                   WHERE ats.semester_id=sem.id) AS attendance_records
           FROM semesters sem WHERE sem.id=%s""",
        (cohort_id,),
    )


def create_cohort(programme_id, data):
    return _write(
        """INSERT INTO semesters
               (course_id, semester_number, section, academic_year, is_active)
           VALUES (%s,%s,%s,%s,TRUE)""",
        (programme_id, data["semester_number"], data["section"], data["academic_year"]),
    )


def update_cohort(cohort_id, data):
    return _write(
        """UPDATE semesters SET semester_number=%s, section=%s, academic_year=%s
           WHERE id=%s""",
        (data["semester_number"], data["section"], data["academic_year"], cohort_id),
    )


def set_cohort_active(cohort_id, is_active):
    return _write("UPDATE semesters SET is_active=%s WHERE id=%s", (bool(is_active), cohort_id))


def delete_unused_cohort(cohort_id):
    impact = get_cohort_impact(cohort_id)
    if impact is None:
        return "missing"
    if any(int(impact[field] or 0) for field in (
        "students", "subjects", "timetable_periods", "attendance_sessions", "attendance_records",
    )):
        return "in_use"
    _write("DELETE FROM semesters WHERE id=%s", (cohort_id,))
    return "deleted"


def _write(query, params):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(query, params)
        connection.commit()
        return cursor.lastrowid or cursor.rowcount
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

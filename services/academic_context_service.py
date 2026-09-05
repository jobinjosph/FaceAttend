from db import get_db_connection


def list_active_contexts():
    return _fetch_all(
        """SELECT sem.id, sem.semester_number, sem.section, sem.academic_year,
                  c.id AS course_id, c.code AS course_code, c.name AS course_name
           FROM semesters sem
           JOIN courses c ON c.id=sem.course_id
           WHERE c.is_active=TRUE AND sem.is_active=TRUE
           ORDER BY c.name, c.code, sem.academic_year DESC,
                    sem.semester_number, sem.section"""
    )


def get_active_context(semester_id):
    return _fetch_one(
        """SELECT sem.id, sem.semester_number, sem.section, sem.academic_year,
                  c.id AS course_id, c.code AS course_code, c.name AS course_name
           FROM semesters sem
           JOIN courses c ON c.id=sem.course_id
           WHERE sem.id=%s AND c.is_active=TRUE AND sem.is_active=TRUE""",
        (semester_id,),
    )


def resolve_context(contexts, semester_id=None, programme="", academic_year="",
                    semester=None, section=""):
    if semester_id is not None:
        return next((item for item in contexts if item["id"] == semester_id), None)
    if not contexts:
        return None

    programme = str(programme or "").strip().upper()
    academic_year = str(academic_year or "").strip()
    section = str(section or "").strip().upper()

    if programme:
        programme_contexts = [item for item in contexts if item["course_code"] == programme]
        if not programme_contexts:
            return None
    else:
        programme_contexts = [
            item for item in contexts if item["course_code"] == contexts[0]["course_code"]
        ]

    year_values = _unique(item["academic_year"] for item in programme_contexts)
    selected_year = academic_year if academic_year in year_values else year_values[0]
    year_contexts = [item for item in programme_contexts if item["academic_year"] == selected_year]

    semester_values = _unique(item["semester_number"] for item in year_contexts)
    selected_semester = semester if semester in semester_values else semester_values[0]
    semester_contexts = [
        item for item in year_contexts if item["semester_number"] == selected_semester
    ]

    section_values = _unique(item["section"] for item in semester_contexts)
    selected_section = section if section in section_values else section_values[0]
    return next(item for item in semester_contexts if item["section"] == selected_section)


def build_selector_options(contexts, context):
    programmes = []
    for item in contexts:
        if not any(option["code"] == item["course_code"] for option in programmes):
            programmes.append({"code": item["course_code"], "name": item["course_name"]})
    if context is None:
        return {
            "programmes": programmes, "academic_years": [], "semesters": [], "sections": [],
        }
    programme_contexts = [
        item for item in contexts if item["course_code"] == context["course_code"]
    ]
    year_contexts = [
        item for item in programme_contexts if item["academic_year"] == context["academic_year"]
    ]
    semester_contexts = [
        item for item in year_contexts
        if item["semester_number"] == context["semester_number"]
    ]
    return {
        "programmes": programmes,
        "academic_years": _unique(item["academic_year"] for item in programme_contexts),
        "semesters": _unique(item["semester_number"] for item in year_contexts),
        "sections": _unique(item["section"] for item in semester_contexts),
    }


def _unique(values):
    result = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


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

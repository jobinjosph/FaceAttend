from datetime import date

import mysql.connector
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from decorators.auth import role_required
from services import session_service, timetable_service


admin_sessions_bp = Blueprint("admin_sessions", __name__, url_prefix="/admin/sessions")


@admin_sessions_bp.get("")
@role_required("ADMIN")
def session_list():
    selected = session_service.parse_session_date(request.args.get("date")) or date.today()
    semester_id = request.args.get("semester_id", type=int)
    selected_programme = request.args.get("programme", "").strip().upper()
    selected_semester = request.args.get("semester", type=int)
    try:
        contexts = timetable_service.list_timetable_contexts()
        if not semester_id and selected_programme:
            matching = [item for item in contexts if item["course_code"] == selected_programme]
            context = next(
                (item for item in matching if item["semester_number"] == selected_semester),
                matching[0] if matching else None,
            )
            semester_id = context["id"] if context else None
        else:
            context = timetable_service.get_timetable_context(semester_id)
        if semester_id is not None and context is None:
            abort(404)
    except mysql.connector.Error:
        contexts, context = [], None
    try:
        sessions = (session_service.list_sessions(selected, semester_id)
                    if semester_id else session_service.list_sessions(selected))
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not load attendance sessions: %s", exc)
        sessions = []; flash("Attendance sessions could not be loaded.", "error")
    programmes = []
    for item in contexts:
        if not any(programme["code"] == item["course_code"] for programme in programmes):
            programmes.append({"code": item["course_code"], "name": item["course_name"]})
    semester_options = [
        item for item in contexts
        if context and item["course_code"] == context["course_code"]
    ]
    return render_template(
        "admin/sessions/list.html", sessions=sessions, selected_date=selected.isoformat(),
        context=context, programmes=programmes, semester_options=semester_options,
    )


@admin_sessions_bp.post("/generate")
@role_required("ADMIN")
def generate():
    selected = session_service.parse_session_date(request.form.get("session_date"))
    semester_id = request.form.get("semester_id", type=int)
    if semester_id is not None and timetable_service.get_timetable_context(semester_id) is None:
        abort(404)
    if selected is None:
        flash("Choose a valid session date.", "error")
        return redirect(url_for("admin_sessions.session_list", **({"semester_id": semester_id} if semester_id else {})))
    try:
        count = (session_service.generate_sessions(selected, semester_id)
                 if semester_id else session_service.generate_sessions(selected))
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not generate attendance sessions: %s", exc)
        flash("Sessions could not be generated.", "error")
        return redirect(url_for("admin_sessions.session_list", date=selected.isoformat(), **({"semester_id": semester_id} if semester_id else {})))
    if count:
        flash(f"Generated {count} attendance session(s).", "success")
    else:
        flash("No new sessions were generated. They may already exist or no classes are scheduled.", "success")
    return redirect(url_for("admin_sessions.session_list", date=selected.isoformat(), **({"semester_id": semester_id} if semester_id else {})))

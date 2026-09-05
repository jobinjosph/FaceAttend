from datetime import date

import mysql.connector
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from decorators.auth import role_required
from services import academic_context_service, session_service


admin_sessions_bp = Blueprint("admin_sessions", __name__, url_prefix="/admin/sessions")


@admin_sessions_bp.get("")
@role_required("ADMIN")
def session_list():
    selected = session_service.parse_session_date(request.args.get("date")) or date.today()
    semester_id = request.args.get("semester_id", type=int)
    contexts = academic_context_service.list_active_contexts()
    context = academic_context_service.resolve_context(
        contexts, semester_id=semester_id,
        programme=request.args.get("programme", ""),
        academic_year=request.args.get("academic_year", ""),
        semester=request.args.get("semester", type=int),
        section=request.args.get("section", ""),
    )
    if context is None and (semester_id is not None or request.args.get("programme")):
        abort(404)
    semester_id = context["id"] if context else None
    try:
        sessions = session_service.list_sessions(selected, semester_id) if context else []
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not load attendance sessions: %s", exc)
        sessions = []; flash("Attendance sessions could not be loaded.", "error")
    selector = academic_context_service.build_selector_options(contexts, context)
    return render_template(
        "admin/sessions/list.html", sessions=sessions, selected_date=selected.isoformat(),
        context=context, selector=selector,
    )


@admin_sessions_bp.post("/generate")
@role_required("ADMIN")
def generate():
    selected = session_service.parse_session_date(request.form.get("session_date"))
    semester_id = request.form.get("semester_id", type=int)
    if semester_id is not None:
        context = academic_context_service.get_active_context(semester_id)
        if context is None:
            abort(404)
    else:
        context = academic_context_service.resolve_context(
            academic_context_service.list_active_contexts()
        )
        semester_id = context["id"] if context else None
    if selected is None:
        flash("Choose a valid session date.", "error")
        return redirect(url_for("admin_sessions.session_list", **({"semester_id": semester_id} if semester_id else {})))
    if context is None:
        flash("No active semester group is configured. Add one in Academic Structure first.", "error")
        return redirect(url_for("admin_sessions.session_list", date=selected.isoformat()))
    try:
        count = session_service.generate_sessions(selected, semester_id)
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not generate attendance sessions: %s", exc)
        flash("Sessions could not be generated.", "error")
        return redirect(url_for("admin_sessions.session_list", date=selected.isoformat(), **({"semester_id": semester_id} if semester_id else {})))
    if count:
        flash(f"Generated {count} attendance session(s).", "success")
    else:
        flash("No new sessions were generated. They may already exist or no classes are scheduled.", "success")
    return redirect(url_for("admin_sessions.session_list", date=selected.isoformat(), **({"semester_id": semester_id} if semester_id else {})))

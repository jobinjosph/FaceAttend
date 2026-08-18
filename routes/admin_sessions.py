from datetime import date

import mysql.connector
from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from decorators.auth import role_required
from services import session_service


admin_sessions_bp = Blueprint("admin_sessions", __name__, url_prefix="/admin/sessions")


@admin_sessions_bp.get("")
@role_required("ADMIN")
def session_list():
    selected = session_service.parse_session_date(request.args.get("date")) or date.today()
    try:
        sessions = session_service.list_sessions(selected)
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not load attendance sessions: %s", exc)
        sessions = []; flash("Attendance sessions could not be loaded.", "error")
    return render_template("admin/sessions/list.html", sessions=sessions, selected_date=selected.isoformat())


@admin_sessions_bp.post("/generate")
@role_required("ADMIN")
def generate():
    selected = session_service.parse_session_date(request.form.get("session_date"))
    if selected is None:
        flash("Choose a valid session date.", "error")
        return redirect(url_for("admin_sessions.session_list"))
    try:
        count = session_service.generate_sessions(selected)
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not generate attendance sessions: %s", exc)
        flash("Sessions could not be generated.", "error")
        return redirect(url_for("admin_sessions.session_list", date=selected.isoformat()))
    if count:
        flash(f"Generated {count} attendance session(s).", "success")
    else:
        flash("No new sessions were generated. They may already exist or no classes are scheduled.", "success")
    return redirect(url_for("admin_sessions.session_list", date=selected.isoformat()))

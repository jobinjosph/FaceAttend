from datetime import date

import mysql.connector
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for

from decorators.auth import role_required
from services import session_service


faculty_sessions_bp = Blueprint("faculty_sessions", __name__, url_prefix="/faculty/sessions")


@faculty_sessions_bp.get("")
@role_required("FACULTY")
def session_list():
    selected = session_service.parse_session_date(request.args.get("date")) or date.today()
    sessions = session_service.list_faculty_sessions(session["user_id"], selected)
    return render_template("faculty/sessions/list.html", sessions=sessions, selected_date=selected.isoformat())


@faculty_sessions_bp.post("/<int:session_id>/start")
@role_required("FACULTY")
def start(session_id):
    result = session_service.start_session(session_id, session["user_id"])
    if result == "not_found": abort(404)
    if result == "already_active": flash("Finish your active session before starting another.", "error")
    elif result == "invalid_status": flash("Only a scheduled session can be started.", "error")
    else: flash("Attendance session started.", "success")
    return redirect(url_for("faculty_sessions.session_list"))


def change_status(session_id, expected, new, message):
    if session_service.get_faculty_session(session_id, session["user_id"]) is None: abort(404)
    if session_service.transition_session(session_id, session["user_id"], expected, new):
        flash(message, "success")
    else: flash(f"This session cannot move from {expected.title()} to {new.title()}.", "error")
    return redirect(url_for("faculty_sessions.session_list"))


@faculty_sessions_bp.post("/<int:session_id>/end")
@role_required("FACULTY")
def end(session_id): return change_status(session_id, "ACTIVE", "REVIEW", "Session ended and is ready for review.")


@faculty_sessions_bp.post("/<int:session_id>/confirm")
@role_required("FACULTY")
def confirm(session_id): return change_status(session_id, "REVIEW", "CONFIRMED", "Attendance session confirmed.")


@faculty_sessions_bp.post("/<int:session_id>/not-conducted")
@role_required("FACULTY")
def not_conducted(session_id): return change_status(session_id, "SCHEDULED", "NOT_CONDUCTED", "Session marked as not conducted.")

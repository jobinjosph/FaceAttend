from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from decorators.auth import role_required
from services import attendance_service


faculty_attendance_bp = Blueprint("faculty_attendance", __name__, url_prefix="/faculty/sessions")


@faculty_attendance_bp.get("/<int:session_id>/attendance")
@role_required("FACULTY")
def roster(session_id):
    details = attendance_service.get_session_details(session_id, session["user_id"])
    if details is None:
        abort(404)
    students = attendance_service.list_roster(session_id)
    totals = attendance_service.attendance_totals(session_id)
    return render_template(
        "faculty/attendance/roster.html", details=details, students=students,
        totals=totals, statuses=attendance_service.MANUAL_STATUSES,
        editable=details["status"] in attendance_service.EDITABLE_SESSION_STATUSES,
    )


@faculty_attendance_bp.post("/<int:session_id>/attendance/<int:student_id>")
@role_required("FACULTY")
def update_attendance(session_id, student_id):
    data = attendance_service.normalize_attendance_data(request.form)
    errors = attendance_service.validate_attendance_data(data)
    if errors:
        flash(next(iter(errors.values())), "error")
        return redirect(url_for("faculty_attendance.roster", session_id=session_id))
    result = attendance_service.update_record(session_id, student_id, session["user_id"], data)
    if result == "not_found":
        abort(404)
    if result == "locked":
        flash("Confirmed or inactive attendance is locked.", "error")
    else:
        flash("Student attendance updated.", "success")
    return redirect(url_for("faculty_attendance.roster", session_id=session_id))


@faculty_attendance_bp.post("/<int:session_id>/attendance/save-all")
@role_required("FACULTY")
def save_all_attendance(session_id):
    details = attendance_service.get_session_details(session_id, session["user_id"])
    if details is None:
        abort(404)
    students = attendance_service.list_roster(session_id)
    student_ids = [student["student_id"] for student in students]
    records = attendance_service.normalize_bulk_attendance(request.form, student_ids)
    errors = attendance_service.validate_bulk_attendance(records)
    if errors:
        flash("Correct the invalid attendance values and try again.", "error")
        return redirect(url_for("faculty_attendance.roster", session_id=session_id))
    result = attendance_service.update_records_bulk(
        session_id, session["user_id"], records
    )
    if result == "not_found":
        abort(404)
    if result == "locked":
        flash("Confirmed or inactive attendance is locked.", "error")
    elif result == "incomplete":
        flash("The roster changed. Refresh the page before saving again.", "error")
    else:
        flash(f"Saved attendance for {len(records)} student(s).", "success")
    return redirect(url_for("faculty_attendance.roster", session_id=session_id))

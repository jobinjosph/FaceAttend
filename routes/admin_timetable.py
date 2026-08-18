import mysql.connector
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from decorators.auth import role_required
from services import timetable_service


admin_timetable_bp = Blueprint("admin_timetable", __name__, url_prefix="/admin/timetable")


def render_period_form(period=None, errors=None, status=200):
    try:
        assignments = timetable_service.get_assignment_options()
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not load timetable options: %s", exc)
        assignments, status = [], 503
        flash("Timetable options could not be loaded.", "error")
    return render_template("admin/timetable/form.html", period=period or {}, errors=errors or {}, assignments=assignments, days=timetable_service.DAYS), status


@admin_timetable_bp.get("")
@role_required("ADMIN")
def timetable_list():
    try:
        periods = timetable_service.list_periods()
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not load timetable: %s", exc)
        periods = []
        flash("The timetable could not be loaded.", "error")
    weekly = {day: [] for day in timetable_service.DAYS}
    for period in periods:
        if period["day_of_week"] in weekly:
            weekly[period["day_of_week"]].append(period)
    return render_template("admin/timetable/list.html", weekly=weekly, days=timetable_service.DAYS, has_periods=bool(periods))


def validate_and_resolve(data, exclude_period_id=None):
    errors = timetable_service.validate_period_data(data)
    assignment = None
    if not errors and data["assignment_id"]:
        assignment = timetable_service.get_assignment(data["assignment_id"])
        if assignment is None:
            errors["assignment_id"] = "Select a current active faculty assignment."
    elif not errors:
        assignment = timetable_service.get_mca_semester_three()
        if assignment is None:
            errors["activity_name"] = "MCA Semester 3 is not configured."
        else:
            assignment.update(subject_id=None, faculty_id=None)
    if not errors:
        conflict = timetable_service.find_conflict(data, assignment, exclude_period_id)
        if conflict == "semester":
            errors["start_time"] = "This class overlaps another Semester 3 period."
        elif conflict == "faculty":
            errors["start_time"] = "This faculty member is teaching another class at that time."
    return errors, assignment


@admin_timetable_bp.route("/add", methods=["GET", "POST"])
@role_required("ADMIN")
def add_period():
    if request.method == "GET":
        return render_period_form()
    data = timetable_service.normalize_period_data(request.form)
    errors, assignment = validate_and_resolve(data)
    if errors:
        return render_period_form(data, errors, 400)
    try:
        timetable_service.create_period(data, assignment)
    except mysql.connector.IntegrityError:
        errors["period_number"] = "That period number is already used on this day."
        return render_period_form(data, errors, 409)
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not create timetable period: %s", exc)
        flash("The timetable period could not be saved.", "error")
        return render_period_form(data, status=503)
    flash("Timetable period added successfully.", "success")
    return redirect(url_for("admin_timetable.timetable_list"))


@admin_timetable_bp.route("/<int:period_id>/edit", methods=["GET", "POST"])
@role_required("ADMIN")
def edit_period(period_id):
    period = timetable_service.get_period(period_id)
    if period is None:
        abort(404)
    if request.method == "GET":
        return render_period_form(period)
    data = timetable_service.normalize_period_data(request.form)
    data["id"] = period_id
    errors, assignment = validate_and_resolve(data, period_id)
    if errors:
        return render_period_form(data, errors, 400)
    try:
        timetable_service.update_period(period_id, data, assignment)
    except mysql.connector.IntegrityError:
        errors["period_number"] = "That period number is already used on this day."
        return render_period_form(data, errors, 409)
    flash("Timetable period updated successfully.", "success")
    return redirect(url_for("admin_timetable.timetable_list"))


@admin_timetable_bp.post("/<int:period_id>/remove")
@role_required("ADMIN")
def remove_period(period_id):
    if timetable_service.get_period(period_id) is None:
        abort(404)
    try:
        timetable_service.delete_period(period_id)
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not remove timetable period: %s", exc)
        flash("The timetable period could not be removed.", "error")
        return redirect(url_for("admin_timetable.timetable_list"))
    flash("Timetable period removed.", "success")
    return redirect(url_for("admin_timetable.timetable_list"))

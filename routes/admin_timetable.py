import mysql.connector
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from decorators.auth import role_required
from services import timetable_service


admin_timetable_bp = Blueprint("admin_timetable", __name__, url_prefix="/admin/timetable")


def render_period_form(period=None, errors=None, status=200, semester_id=None):
    semester_id=semester_id or (period or {}).get("semester_id")
    try:
        assignments=timetable_service.get_assignment_options(semester_id) if semester_id else timetable_service.get_assignment_options()
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not load timetable options: %s", exc)
        assignments, status = [], 503
        flash("Timetable options could not be loaded.", "error")
    try:
        context=timetable_service.get_timetable_context(semester_id)
    except mysql.connector.Error:
        context={"id":semester_id,"course_code":"MCA","course_name":"Master of Computer Applications","semester_number":3,"section":"A","academic_year":""}
    return render_template("admin/timetable/form.html",period=period or {},errors=errors or {},assignments=assignments,days=timetable_service.DAYS,context=context),status


@admin_timetable_bp.get("")
@role_required("ADMIN")
def timetable_list():
    semester_id=request.args.get("semester_id",type=int)
    selected_programme=request.args.get("programme","").strip().upper()
    selected_semester=request.args.get("semester",type=int)
    try:
        contexts=timetable_service.list_timetable_contexts()
        if not semester_id and selected_programme:
            matching=[item for item in contexts if item["course_code"]==selected_programme]
            context=next((item for item in matching if item["semester_number"]==selected_semester),matching[0] if matching else None)
            semester_id=context["id"] if context else None
        else:
            context=timetable_service.get_timetable_context(semester_id)
    except mysql.connector.Error:
        contexts=[]; context=None
    try:
        periods=timetable_service.list_periods(semester_id) if semester_id else timetable_service.list_periods()
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not load timetable: %s", exc)
        periods=[]
        flash("The timetable could not be loaded.", "error")
    programmes=[]
    for item in contexts:
        if not any(programme["code"]==item["course_code"] for programme in programmes):
            programmes.append({"code":item["course_code"],"name":item["course_name"]})
    semester_options=[item for item in contexts if context and item["course_code"]==context["course_code"]]
    weekly = {day: [] for day in timetable_service.DAYS}
    for period in periods:
        if period["day_of_week"] in weekly:
            weekly[period["day_of_week"]].append(period)
    return render_template("admin/timetable/list.html",weekly=weekly,days=timetable_service.DAYS,has_periods=bool(periods),context=context,programmes=programmes,semester_options=semester_options)


def validate_and_resolve(data, exclude_period_id=None, semester_id=None):
    errors = timetable_service.validate_period_data(data)
    assignment = None
    if not errors and data["assignment_id"]:
        assignment=timetable_service.get_assignment(data["assignment_id"],semester_id) if semester_id else timetable_service.get_assignment(data["assignment_id"])
        if assignment is None:
            errors["assignment_id"] = "Select a current active faculty assignment."
    elif not errors:
        assignment={"semester_id":semester_id} if semester_id else timetable_service.get_mca_semester_three()
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
    semester_id=request.values.get("semester_id",type=int)
    if request.method == "GET":
        return render_period_form(semester_id=semester_id)
    data = timetable_service.normalize_period_data(request.form)
    errors, assignment = validate_and_resolve(data,semester_id=semester_id)
    if errors:
        return render_period_form(data,errors,400,semester_id)
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
    return redirect(url_for("admin_timetable.timetable_list",**({"semester_id":semester_id} if semester_id else {})))


@admin_timetable_bp.route("/<int:period_id>/edit", methods=["GET", "POST"])
@role_required("ADMIN")
def edit_period(period_id):
    period = timetable_service.get_period(period_id)
    if period is None:
        abort(404)
    if request.method == "GET":
        return render_period_form(period,semester_id=period.get("semester_id"))
    data = timetable_service.normalize_period_data(request.form)
    data["id"] = period_id
    errors, assignment = validate_and_resolve(data,period_id,period.get("semester_id"))
    if errors:
        return render_period_form(data, errors, 400)
    try:
        timetable_service.update_period(period_id, data, assignment)
    except mysql.connector.IntegrityError:
        errors["period_number"] = "That period number is already used on this day."
        return render_period_form(data, errors, 409)
    flash("Timetable period updated successfully.", "success")
    return redirect(url_for("admin_timetable.timetable_list",**({"semester_id":period.get('semester_id')} if period.get('semester_id') else {})))


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
    semester_id=request.form.get("semester_id",type=int)
    return redirect(url_for("admin_timetable.timetable_list",**({"semester_id":semester_id} if semester_id else {})))

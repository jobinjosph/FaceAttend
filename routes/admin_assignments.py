import mysql.connector
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from decorators.auth import role_required
from services import assignment_service


admin_assignments_bp = Blueprint(
    "admin_assignments", __name__, url_prefix="/admin/faculty-subjects"
)


def render_assignment_form(assignment=None, errors=None, status=200):
    try:
        subjects, faculty = assignment_service.get_assignment_options()
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not load assignment options: %s", exc)
        subjects, faculty = [], []
        flash("Assignment options could not be loaded.", "error")
        status = 503
    return render_template(
        "admin/assignments/form.html",
        assignment=assignment or {}, errors=errors or {}, subjects=subjects, faculty=faculty,
    ), status


@admin_assignments_bp.get("")
@role_required("ADMIN")
def assignment_list():
    try:
        assignments = assignment_service.list_assignments()
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not list faculty subject assignments: %s", exc)
        assignments = []
        flash("Faculty assignments could not be loaded.", "error")
    return render_template("admin/assignments/list.html", assignments=assignments)


@admin_assignments_bp.route("/add", methods=["GET", "POST"])
@role_required("ADMIN")
def add_assignment():
    if request.method == "GET":
        return render_assignment_form()
    data = assignment_service.normalize_assignment_data(request.form)
    errors = assignment_service.validate_assignment_data(data)
    if not errors and not assignment_service.active_subject_exists(data["subject_id"]):
        errors["subject_id"] = "Select an active MCA Semester 3 subject."
    if not errors and not assignment_service.active_faculty_exists(data["faculty_id"]):
        errors["faculty_id"] = "Select an active faculty member."
    if errors:
        return render_assignment_form(data, errors, 400)
    try:
        assignment_service.create_assignment(data)
    except mysql.connector.IntegrityError:
        errors["faculty_id"] = "This faculty member is already assigned to that subject."
        return render_assignment_form(data, errors, 409)
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not create faculty subject assignment: %s", exc)
        flash("The faculty assignment could not be saved.", "error")
        return render_assignment_form(data, status=503)
    flash("Faculty assigned to subject successfully.", "success")
    return redirect(url_for("admin_assignments.assignment_list"))


@admin_assignments_bp.post("/<int:assignment_id>/remove")
@role_required("ADMIN")
def remove_assignment(assignment_id):
    if assignment_service.get_assignment(assignment_id) is None:
        abort(404)
    try:
        assignment_service.delete_assignment(assignment_id)
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not remove faculty subject assignment: %s", exc)
        flash("The faculty assignment could not be removed.", "error")
        return redirect(url_for("admin_assignments.assignment_list"))
    flash("Faculty assignment removed.", "success")
    return redirect(url_for("admin_assignments.assignment_list"))

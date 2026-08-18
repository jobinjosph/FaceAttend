import mysql.connector
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from decorators.auth import role_required
from services import subject_service


admin_subjects_bp = Blueprint("admin_subjects", __name__, url_prefix="/admin/subjects")


def render_subject_form(subject=None, errors=None, status=200):
    return render_template(
        "admin/subjects/form.html",
        subject=subject or {},
        errors=errors or {},
        activity_types=subject_service.ACTIVITY_TYPES,
    ), status


@admin_subjects_bp.get("")
@role_required("ADMIN")
def subject_list():
    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "all")
    if status_filter not in {"all", "active", "inactive"}:
        status_filter = "all"
    try:
        subjects = subject_service.list_semester_three_subjects(search, status_filter)
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not list subjects: %s", exc)
        flash("Subjects could not be loaded. Please try again.", "error")
        subjects = []
    return render_template(
        "admin/subjects/list.html", subjects=subjects, search=search, status_filter=status_filter
    )


@admin_subjects_bp.route("/add", methods=["GET", "POST"])
@role_required("ADMIN")
def add_subject():
    if request.method == "GET":
        return render_subject_form()
    data = subject_service.normalize_subject_data(request.form)
    errors = subject_service.validate_subject_data(data)
    if errors:
        return render_subject_form(data, errors, 400)
    semester = subject_service.get_mca_semester_three()
    if semester is None:
        flash("MCA Semester 3 is not configured. Run python init_db.py first.", "error")
        return render_subject_form(data, status=503)
    try:
        subject_service.create_subject(data, semester["id"])
    except mysql.connector.IntegrityError:
        errors["subject_code"] = "This subject code is already in use."
        return render_subject_form(data, errors, 409)
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not add subject: %s", exc)
        flash("The subject could not be saved.", "error")
        return render_subject_form(data, status=503)
    flash("Semester 3 subject added successfully.", "success")
    return redirect(url_for("admin_subjects.subject_list"))


@admin_subjects_bp.route("/<int:subject_id>/edit", methods=["GET", "POST"])
@role_required("ADMIN")
def edit_subject(subject_id):
    subject = subject_service.get_subject(subject_id)
    if subject is None:
        abort(404)
    if request.method == "GET":
        return render_subject_form(subject)
    data = subject_service.normalize_subject_data(request.form)
    errors = subject_service.validate_subject_data(data)
    if errors:
        data["id"] = subject_id
        return render_subject_form(data, errors, 400)
    try:
        subject_service.update_subject(subject_id, data)
    except mysql.connector.IntegrityError:
        errors["subject_code"] = "This subject code is already in use."
        data["id"] = subject_id
        return render_subject_form(data, errors, 409)
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not update subject: %s", exc)
        flash("The subject could not be updated.", "error")
        data["id"] = subject_id
        return render_subject_form(data, status=503)
    flash("Subject updated successfully.", "success")
    return redirect(url_for("admin_subjects.subject_list"))


@admin_subjects_bp.post("/<int:subject_id>/status")
@role_required("ADMIN")
def change_subject_status(subject_id):
    if subject_service.get_subject(subject_id) is None:
        abort(404)
    is_active = request.form.get("is_active") == "1"
    try:
        subject_service.set_subject_active(subject_id, is_active)
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not change subject status: %s", exc)
        flash("Subject status could not be changed.", "error")
        return redirect(url_for("admin_subjects.subject_list"))
    flash("Subject activated." if is_active else "Subject deactivated.", "success")
    return redirect(url_for("admin_subjects.subject_list"))

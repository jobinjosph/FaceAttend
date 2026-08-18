import mysql.connector
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from decorators.auth import role_required
from services import faculty_service


admin_faculty_bp = Blueprint(
    "admin_faculty",
    __name__,
    url_prefix="/admin/faculty",
)


def render_faculty_form(faculty=None, errors=None, status=200):
    return (
        render_template(
            "admin/faculty/form.html",
            faculty=faculty or {},
            errors=errors or {},
        ),
        status,
    )


@admin_faculty_bp.get("")
@role_required("ADMIN")
def faculty_list():
    try:
        faculty = faculty_service.list_faculty()
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not list faculty: %s", exc)
        flash("Faculty could not be loaded. Please try again.", "error")
        faculty = []
    return render_template("admin/faculty/list.html", faculty=faculty)


@admin_faculty_bp.route("/add", methods=["GET", "POST"])
@role_required("ADMIN")
def add_faculty():
    if request.method == "GET":
        return render_faculty_form()

    data = faculty_service.normalize_faculty_data(request.form)
    errors = faculty_service.validate_faculty_data(data, require_password=True)
    if errors:
        data["password"] = ""
        return render_faculty_form(data, errors, 400)

    try:
        faculty_service.create_faculty(data)
    except mysql.connector.IntegrityError:
        errors["employee_code"] = "Employee code or email is already in use."
        data["password"] = ""
        return render_faculty_form(data, errors, 409)
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not add faculty: %s", exc)
        flash("The faculty account could not be saved. Please try again.", "error")
        data["password"] = ""
        return render_faculty_form(data, status=503)

    flash("Faculty member and login account created successfully.", "success")
    return redirect(url_for("admin_faculty.faculty_list"))


@admin_faculty_bp.route("/<int:faculty_id>/edit", methods=["GET", "POST"])
@role_required("ADMIN")
def edit_faculty(faculty_id):
    existing_faculty = faculty_service.get_faculty(faculty_id)
    if existing_faculty is None:
        abort(404)

    if request.method == "GET":
        return render_faculty_form(existing_faculty)

    data = faculty_service.normalize_faculty_data(request.form)
    errors = faculty_service.validate_faculty_data(data, require_password=False)
    if errors:
        data["id"] = faculty_id
        data["password"] = ""
        return render_faculty_form(data, errors, 400)

    try:
        faculty_service.update_faculty(faculty_id, data)
    except mysql.connector.IntegrityError:
        errors["employee_code"] = "Employee code or email is already in use."
        data["id"] = faculty_id
        data["password"] = ""
        return render_faculty_form(data, errors, 409)
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not update faculty: %s", exc)
        flash("The faculty account could not be updated.", "error")
        data["id"] = faculty_id
        data["password"] = ""
        return render_faculty_form(data, status=503)

    flash("Faculty details updated successfully.", "success")
    return redirect(url_for("admin_faculty.faculty_list"))


@admin_faculty_bp.post("/<int:faculty_id>/status")
@role_required("ADMIN")
def change_faculty_status(faculty_id):
    faculty = faculty_service.get_faculty(faculty_id)
    if faculty is None:
        abort(404)

    is_active = request.form.get("is_active") == "1"
    try:
        faculty_service.set_faculty_active(faculty_id, is_active)
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not change faculty status: %s", exc)
        flash("Faculty status could not be changed.", "error")
        return redirect(url_for("admin_faculty.faculty_list"))

    message = "Faculty account activated." if is_active else "Faculty account deactivated."
    flash(message, "success")
    return redirect(url_for("admin_faculty.faculty_list"))

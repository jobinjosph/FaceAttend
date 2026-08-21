import mysql.connector
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from decorators.auth import role_required
from services import student_service


admin_students_bp = Blueprint(
    "admin_students",
    __name__,
    url_prefix="/admin/students",
)


def render_student_form(student=None, errors=None, status=200):
    courses, semesters = student_service.get_academic_options()
    return (
        render_template(
            "admin/students/form.html",
            student=student or {},
            errors=errors or {},
            courses=courses,
            semesters=semesters,
        ),
        status,
    )


@admin_students_bp.get("")
@role_required("ADMIN")
def student_list():
    try:
        students = student_service.list_students()
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not list students: %s", exc)
        flash("Students could not be loaded. Please try again.", "error")
        students = []
    return render_template("admin/students/list.html", students=students)


@admin_students_bp.route("/add", methods=["GET", "POST"])
@role_required("ADMIN")
def add_student():
    if request.method == "GET":
        return render_student_form()

    data = student_service.normalize_student_data(request.form)
    errors = student_service.validate_student_data(data, require_password=True)
    if not errors and not student_service.semester_belongs_to_course(
        data["semester_id"], data["course_id"]
    ):
        errors["semester_id"] = "Select a semester belonging to this course."

    if errors:
        return render_student_form(data, errors, 400)

    try:
        student_service.create_student(data)
    except mysql.connector.IntegrityError as exc:
        if "email" in str(exc).lower():
            errors["email"] = "This email address is already used by another account."
        else:
            errors["register_number"] = "This register number is already in use."
        return render_student_form(data, errors, 409)
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not add student: %s", exc)
        flash("The student could not be saved. Please try again.", "error")
        return render_student_form(data, status=503)

    flash("Student and login account added successfully.", "success")
    return redirect(url_for("admin_students.student_list"))


@admin_students_bp.route("/<int:student_id>/edit", methods=["GET", "POST"])
@role_required("ADMIN")
def edit_student(student_id):
    existing_student = student_service.get_student(student_id)
    if existing_student is None:
        abort(404)

    if request.method == "GET":
        return render_student_form(existing_student)

    data = student_service.normalize_student_data(request.form)
    errors = student_service.validate_student_data(
        data, require_password=not bool(existing_student.get("user_id"))
    )
    if not errors and not student_service.semester_belongs_to_course(
        data["semester_id"], data["course_id"]
    ):
        errors["semester_id"] = "Select a semester belonging to this course."

    if errors:
        data["id"] = student_id
        data["user_id"] = existing_student.get("user_id")
        return render_student_form(data, errors, 400)

    try:
        student_service.update_student(student_id, data)
    except mysql.connector.IntegrityError as exc:
        if "email" in str(exc).lower():
            errors["email"] = "This email address is already used by another account."
        else:
            errors["register_number"] = "This register number is already in use."
        data["id"] = student_id
        data["user_id"] = existing_student.get("user_id")
        return render_student_form(data, errors, 409)
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not update student: %s", exc)
        flash("The student could not be updated. Please try again.", "error")
        data["id"] = student_id
        data["user_id"] = existing_student.get("user_id")
        return render_student_form(data, status=503)

    flash("Student updated successfully.", "success")
    return redirect(url_for("admin_students.student_list"))


@admin_students_bp.post("/<int:student_id>/status")
@role_required("ADMIN")
def change_student_status(student_id):
    student = student_service.get_student(student_id)
    if student is None:
        abort(404)

    is_active = request.form.get("is_active") == "1"
    try:
        student_service.set_student_active(student_id, is_active)
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not change student status: %s", exc)
        flash("Student status could not be changed.", "error")
        return redirect(url_for("admin_students.student_list"))

    message = "Student activated." if is_active else "Student deactivated."
    flash(message, "success")
    return redirect(url_for("admin_students.student_list"))

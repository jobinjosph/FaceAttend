import mysql.connector
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for

from decorators.auth import role_required
from services import academic_context_service, student_service


admin_students_bp = Blueprint(
    "admin_students",
    __name__,
    url_prefix="/admin/students",
)


def render_student_form(student=None, errors=None, status=200, semester_id=None):
    student = student or {}
    semester_id = semester_id or student.get("semester_id")
    contexts = academic_context_service.list_active_contexts()
    context = academic_context_service.resolve_context(contexts, semester_id=semester_id)
    return (
        render_template(
            "admin/students/form.html",
            student=student,
            errors=errors or {},
            contexts=contexts,
            context=context,
        ),
        status,
    )


@admin_students_bp.get("")
@role_required("ADMIN")
def student_list():
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
    try:
        students = student_service.list_students(context["id"]) if context else []
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not list students: %s", exc)
        flash("Students could not be loaded. Please try again.", "error")
        students = []
    return render_template(
        "admin/students/list.html", students=students, context=context,
        selector=academic_context_service.build_selector_options(contexts, context),
    )


@admin_students_bp.route("/placement", methods=["GET", "POST"])
@role_required("ADMIN")
def manage_placement():
    source_semester_id = request.values.get("semester_id", type=int)
    contexts = academic_context_service.list_active_contexts()
    source = academic_context_service.resolve_context(contexts, semester_id=source_semester_id)
    if source is None:
        abort(404)

    students = student_service.list_students(source["id"])
    if request.method == "GET":
        return render_template(
            "admin/students/placement.html", source=source, contexts=contexts,
            students=students, selected_ids=[], destination_id=None,
        )

    selected_ids = request.form.getlist("student_id", type=int)
    destination_id = request.form.get("destination_semester_id", type=int)
    errors = []
    if not selected_ids:
        errors.append("Select at least one student.")
    if destination_id is None:
        errors.append("Select a destination group.")
    elif destination_id == source["id"]:
        errors.append("Select a destination different from the current group.")
    elif academic_context_service.resolve_context(contexts, semester_id=destination_id) is None:
        errors.append("The selected destination is not active.")

    if errors:
        return render_template(
            "admin/students/placement.html", source=source, contexts=contexts,
            students=students, selected_ids=selected_ids, destination_id=destination_id,
            errors=errors,
        ), 400

    try:
        moved_count = student_service.move_students(
            selected_ids, source["id"], destination_id, session["user_id"]
        )
    except ValueError as exc:
        return render_template(
            "admin/students/placement.html", source=source, contexts=contexts,
            students=students, selected_ids=selected_ids, destination_id=destination_id,
            errors=[str(exc)],
        ), 400
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not move students: %s", exc)
        flash("Student placement could not be updated. Please try again.", "error")
        return redirect(url_for("admin_students.manage_placement", semester_id=source["id"]))

    flash(f"{moved_count} student{'s' if moved_count != 1 else ''} moved successfully.", "success")
    return redirect(url_for("admin_students.student_list", semester_id=destination_id))


@admin_students_bp.get("/<int:student_id>/placement-history")
@role_required("ADMIN")
def placement_history(student_id):
    student = student_service.get_student(student_id)
    if student is None:
        abort(404)
    try:
        history = student_service.get_placement_history(student_id)
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not load student placement history: %s", exc)
        flash("Placement history could not be loaded. Please try again.", "error")
        history = []
    return render_template("admin/students/placement_history.html", student=student, history=history)


@admin_students_bp.route("/add", methods=["GET", "POST"])
@role_required("ADMIN")
def add_student():
    semester_id = request.values.get("semester_id", type=int)
    if request.method == "GET":
        if semester_id is not None and academic_context_service.get_active_context(semester_id) is None:
            abort(404)
        return render_student_form(semester_id=semester_id)

    data = student_service.normalize_student_data(request.form)
    errors = student_service.validate_student_data(data, require_password=True)
    if not errors and not student_service.active_semester_belongs_to_course(
        data["semester_id"], data["course_id"]
    ):
        errors["semester_id"] = "Select a semester belonging to this course."

    if errors:
        return render_student_form(data, errors, 400, semester_id)

    try:
        student_service.create_student(data)
    except mysql.connector.IntegrityError as exc:
        if "email" in str(exc).lower():
            errors["email"] = "This email address is already used by another account."
        else:
            errors["register_number"] = "This register number is already in use."
        return render_student_form(data, errors, 409, semester_id)
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not add student: %s", exc)
        flash("The student could not be saved. Please try again.", "error")
        return render_student_form(data, status=503, semester_id=semester_id)

    flash("Student and login account added successfully.", "success")
    return redirect(url_for("admin_students.student_list", semester_id=data["semester_id"]))


@admin_students_bp.route("/<int:student_id>/edit", methods=["GET", "POST"])
@role_required("ADMIN")
def edit_student(student_id):
    existing_student = student_service.get_student(student_id)
    if existing_student is None:
        abort(404)

    if request.method == "GET":
        return render_student_form(existing_student, semester_id=existing_student.get("semester_id"))

    data = student_service.normalize_student_data(request.form)
    errors = student_service.validate_student_data(
        data, require_password=not bool(existing_student.get("user_id"))
    )
    unchanged_group = (
        data.get("semester_id") == existing_student.get("semester_id")
        and data.get("course_id") == existing_student.get("course_id")
    )
    if not errors and not unchanged_group and not student_service.active_semester_belongs_to_course(
        data["semester_id"], data["course_id"]
    ):
        errors["semester_id"] = "Select a semester belonging to this course."

    if errors:
        data["id"] = student_id
        data["user_id"] = existing_student.get("user_id")
        return render_student_form(data, errors, 400, data.get("semester_id"))

    try:
        student_service.update_student(student_id, data, session["user_id"])
    except mysql.connector.IntegrityError as exc:
        if "email" in str(exc).lower():
            errors["email"] = "This email address is already used by another account."
        else:
            errors["register_number"] = "This register number is already in use."
        data["id"] = student_id
        data["user_id"] = existing_student.get("user_id")
        return render_student_form(data, errors, 409, data.get("semester_id"))
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not update student: %s", exc)
        flash("The student could not be updated. Please try again.", "error")
        data["id"] = student_id
        data["user_id"] = existing_student.get("user_id")
        return render_student_form(data, status=503, semester_id=data.get("semester_id"))

    flash("Student updated successfully.", "success")
    return redirect(url_for("admin_students.student_list", semester_id=data["semester_id"]))


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
        return redirect(url_for("admin_students.student_list", semester_id=student.get("semester_id")))

    message = "Student activated." if is_active else "Student deactivated."
    flash(message, "success")
    return redirect(url_for("admin_students.student_list", semester_id=student.get("semester_id")))

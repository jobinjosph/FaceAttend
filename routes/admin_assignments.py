import mysql.connector
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from decorators.auth import role_required
from services import assignment_service, timetable_service


admin_assignments_bp = Blueprint(
    "admin_assignments", __name__, url_prefix="/admin/faculty-subjects"
)


def render_assignment_form(assignment=None, errors=None, status=200, semester_id=None):
    semester_id = semester_id or (assignment or {}).get("semester_id")
    try:
        subjects, faculty = (assignment_service.get_assignment_options(semester_id)
                             if semester_id else assignment_service.get_assignment_options())
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not load assignment options: %s", exc)
        subjects, faculty = [], []
        flash("Assignment options could not be loaded.", "error")
        status = 503
    try:
        context = timetable_service.get_timetable_context(semester_id)
    except mysql.connector.Error:
        if semester_id is not None:
            raise
        context = None
    if semester_id is not None and context is None:
        abort(404)
    return render_template(
        "admin/assignments/form.html",
        assignment=assignment or {}, errors=errors or {}, subjects=subjects, faculty=faculty,
        context=context,
    ), status


@admin_assignments_bp.get("")
@role_required("ADMIN")
def assignment_list():
    semester_id = request.args.get("semester_id", type=int)
    selected_programme = request.args.get("programme", "").strip().upper()
    selected_semester = request.args.get("semester", type=int)
    try:
        contexts = timetable_service.list_timetable_contexts()
        if not semester_id and selected_programme:
            matching = [item for item in contexts if item["course_code"] == selected_programme]
            context = next(
                (item for item in matching if item["semester_number"] == selected_semester),
                matching[0] if matching else None,
            )
            semester_id = context["id"] if context else None
        else:
            context = timetable_service.get_timetable_context(semester_id)
        if semester_id is not None and context is None:
            abort(404)
    except mysql.connector.Error:
        contexts, context = [], None
    try:
        assignments = (assignment_service.list_assignments(semester_id)
                       if semester_id else assignment_service.list_assignments())
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not list faculty subject assignments: %s", exc)
        assignments = []
        flash("Faculty assignments could not be loaded.", "error")
    programmes = []
    for item in contexts:
        if not any(programme["code"] == item["course_code"] for programme in programmes):
            programmes.append({"code": item["course_code"], "name": item["course_name"]})
    semester_options = [
        item for item in contexts
        if context and item["course_code"] == context["course_code"]
    ]
    return render_template(
        "admin/assignments/list.html", assignments=assignments, context=context,
        programmes=programmes, semester_options=semester_options,
    )


@admin_assignments_bp.route("/add", methods=["GET", "POST"])
@role_required("ADMIN")
def add_assignment():
    semester_id = request.values.get("semester_id", type=int)
    if semester_id is not None and timetable_service.get_timetable_context(semester_id) is None:
        abort(404)
    if request.method == "GET":
        return render_assignment_form(semester_id=semester_id)
    data = assignment_service.normalize_assignment_data(request.form)
    errors = assignment_service.validate_assignment_data(data)
    if not errors:
        subject_exists = (assignment_service.active_subject_exists(data["subject_id"], semester_id)
                          if semester_id else assignment_service.active_subject_exists(data["subject_id"]))
        if not subject_exists:
            errors["subject_id"] = "Select an active subject from the selected programme and semester."
    if not errors and not assignment_service.active_faculty_exists(data["faculty_id"]):
        errors["faculty_id"] = "Select an active faculty member."
    if errors:
        return render_assignment_form(data, errors, 400, semester_id)
    try:
        assignment_service.create_assignment(data)
    except mysql.connector.IntegrityError:
        errors["faculty_id"] = "This faculty member is already assigned to that subject."
        return render_assignment_form(data, errors, 409, semester_id)
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not create faculty subject assignment: %s", exc)
        flash("The faculty assignment could not be saved.", "error")
        return render_assignment_form(data, status=503, semester_id=semester_id)
    flash("Faculty assigned to subject successfully.", "success")
    return redirect(url_for("admin_assignments.assignment_list", **({"semester_id": semester_id} if semester_id else {})))


@admin_assignments_bp.post("/<int:assignment_id>/remove")
@role_required("ADMIN")
def remove_assignment(assignment_id):
    assignment = assignment_service.get_assignment(assignment_id)
    if assignment is None:
        abort(404)
    semester_id = assignment.get("semester_id")
    try:
        assignment_service.delete_assignment(assignment_id)
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not remove faculty subject assignment: %s", exc)
        flash("The faculty assignment could not be removed.", "error")
        return redirect(url_for("admin_assignments.assignment_list", **({"semester_id": semester_id} if semester_id else {})))
    flash("Faculty assignment removed.", "success")
    return redirect(url_for("admin_assignments.assignment_list", **({"semester_id": semester_id} if semester_id else {})))

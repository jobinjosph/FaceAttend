import mysql.connector
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from decorators.auth import role_required
from services import academic_context_service, assignment_service


admin_assignments_bp = Blueprint(
    "admin_assignments", __name__, url_prefix="/admin/faculty-subjects"
)


def render_assignment_form(assignment=None, errors=None, status=200, semester_id=None):
    semester_id = semester_id or (assignment or {}).get("semester_id")
    context = assignment_context(semester_id)
    try:
        subjects, faculty = (assignment_service.get_assignment_options(context["id"])
                             if context else ([], []))
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not load assignment options: %s", exc)
        subjects, faculty = [], []
        flash("Assignment options could not be loaded.", "error")
        status = 503
    return render_template(
        "admin/assignments/form.html",
        assignment=assignment or {}, errors=errors or {}, subjects=subjects, faculty=faculty,
        context=context,
    ), status


def assignment_context(semester_id):
    if semester_id is not None:
        context = academic_context_service.get_active_context(semester_id)
        if context is None:
            abort(404)
        return context
    return academic_context_service.resolve_context(academic_context_service.list_active_contexts())


@admin_assignments_bp.get("")
@role_required("ADMIN")
def assignment_list():
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
    semester_id = context["id"] if context else None
    try:
        assignments = (assignment_service.list_assignments(semester_id)
                       if context else [])
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not list faculty subject assignments: %s", exc)
        assignments = []
        flash("Faculty assignments could not be loaded.", "error")
    return render_template(
        "admin/assignments/list.html", assignments=assignments, context=context,
        selector=academic_context_service.build_selector_options(contexts, context),
    )


@admin_assignments_bp.route("/add", methods=["GET", "POST"])
@role_required("ADMIN")
def add_assignment():
    semester_id = request.values.get("semester_id", type=int)
    context = assignment_context(semester_id)
    semester_id = context["id"] if context else None
    if request.method == "GET":
        return render_assignment_form(semester_id=semester_id)
    data = assignment_service.normalize_assignment_data(request.form)
    errors = assignment_service.validate_assignment_data(data)
    if context is None:
        flash("No active semester group is configured. Add one in Academic Structure first.", "error")
        return render_assignment_form(data, status=400)
    if not errors:
        subject_exists = assignment_service.active_subject_exists(data["subject_id"], semester_id)
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

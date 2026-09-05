import mysql.connector
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from decorators.auth import role_required
from services import academic_context_service, subject_service


admin_subjects_bp = Blueprint("admin_subjects", __name__, url_prefix="/admin/subjects")


def render_subject_form(subject=None, errors=None, status=200, semester_id=None):
    semester_id = semester_id or (subject or {}).get("semester_id")
    if semester_id is not None:
        context = academic_context_service.get_active_context(semester_id)
    else:
        contexts = academic_context_service.list_active_contexts()
        context = academic_context_service.resolve_context(contexts)
    if semester_id is not None and context is None:
        abort(404)
    return render_template(
        "admin/subjects/form.html",
        subject=subject or {},
        errors=errors or {},
        activity_types=subject_service.ACTIVITY_TYPES,
        context=context,
    ), status


@admin_subjects_bp.get("")
@role_required("ADMIN")
def subject_list():
    semester_id = request.args.get("semester_id", type=int)
    contexts = academic_context_service.list_active_contexts()
    context = academic_context_service.resolve_context(
        contexts,
        semester_id=semester_id,
        programme=request.args.get("programme", ""),
        academic_year=request.args.get("academic_year", ""),
        semester=request.args.get("semester", type=int),
        section=request.args.get("section", ""),
    )
    if semester_id is not None and context is None:
        abort(404)
    if request.args.get("programme") and context is None:
        abort(404)
    semester_id = context["id"] if context else None
    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "all")
    if status_filter not in {"all", "active", "inactive"}:
        status_filter = "all"
    try:
        subjects = subject_service.list_subjects(search, status_filter, semester_id)
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not list subjects: %s", exc)
        flash("Subjects could not be loaded. Please try again.", "error")
        subjects = []
    selector = academic_context_service.build_selector_options(contexts, context)
    return render_template(
        "admin/subjects/list.html", subjects=subjects, search=search,
        status_filter=status_filter, context=context, selector=selector,
    )


@admin_subjects_bp.route("/add", methods=["GET", "POST"])
@role_required("ADMIN")
def add_subject():
    semester_id=request.values.get("semester_id",type=int)
    if request.method == "GET":
        return render_subject_form(semester_id=semester_id)
    data = subject_service.normalize_subject_data(request.form)
    errors = subject_service.validate_subject_data(data)
    if errors:
        return render_subject_form(data,errors,400,semester_id)
    if semester_id:
        semester = academic_context_service.get_active_context(semester_id)
    else:
        contexts = academic_context_service.list_active_contexts()
        semester = academic_context_service.resolve_context(contexts)
    if semester is None:
        if semester_id is not None:
            abort(404)
        flash("No active academic group is configured.", "error")
        return render_subject_form(data,status=503)
    semester_id = semester["id"]
    try:
        subject_service.create_subject(data, semester["id"])
    except mysql.connector.IntegrityError:
        errors["subject_code"] = "This subject code is already in use."
        return render_subject_form(data,errors,409,semester_id)
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not add subject: %s", exc)
        flash("The subject could not be saved.", "error")
        return render_subject_form(data,status=503,semester_id=semester_id)
    flash("Subject added successfully.", "success")
    return redirect(url_for("admin_subjects.subject_list",**({"semester_id":semester_id} if semester_id else {})))


@admin_subjects_bp.route("/<int:subject_id>/edit", methods=["GET", "POST"])
@role_required("ADMIN")
def edit_subject(subject_id):
    semester_id=request.values.get("semester_id",type=int)
    subject=(subject_service.get_subject(subject_id,semester_id) if semester_id else subject_service.get_subject(subject_id))
    if subject is None:
        abort(404)
    semester_id = semester_id or subject.get("semester_id")
    if request.method == "GET":
        return render_subject_form(subject,semester_id=semester_id)
    data = subject_service.normalize_subject_data(request.form)
    errors = subject_service.validate_subject_data(data)
    if errors:
        data["id"] = subject_id
        return render_subject_form(data,errors,400,semester_id)
    try:
        subject_service.update_subject(subject_id, data)
    except mysql.connector.IntegrityError:
        errors["subject_code"] = "This subject code is already in use."
        data["id"] = subject_id
        return render_subject_form(data,errors,409,semester_id)
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not update subject: %s", exc)
        flash("The subject could not be updated.", "error")
        data["id"] = subject_id
        return render_subject_form(data,status=503,semester_id=semester_id)
    flash("Subject updated successfully.", "success")
    return redirect(url_for("admin_subjects.subject_list",**({"semester_id":semester_id} if semester_id else {})))


@admin_subjects_bp.post("/<int:subject_id>/status")
@role_required("ADMIN")
def change_subject_status(subject_id):
    semester_id=request.form.get("semester_id",type=int)
    subject=(subject_service.get_subject(subject_id,semester_id) if semester_id else subject_service.get_subject(subject_id))
    if subject is None:
        abort(404)
    semester_id = semester_id or subject.get("semester_id")
    is_active = request.form.get("is_active") == "1"
    try:
        subject_service.set_subject_active(subject_id, is_active)
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not change subject status: %s", exc)
        flash("Subject status could not be changed.", "error")
        return redirect(url_for("admin_subjects.subject_list",**({"semester_id":semester_id} if semester_id else {})))
    flash("Subject activated." if is_active else "Subject deactivated.", "success")
    return redirect(url_for("admin_subjects.subject_list",**({"semester_id":semester_id} if semester_id else {})))

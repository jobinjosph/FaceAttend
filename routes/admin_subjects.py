import mysql.connector
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from decorators.auth import role_required
from services import subject_service, timetable_service


admin_subjects_bp = Blueprint("admin_subjects", __name__, url_prefix="/admin/subjects")


def render_subject_form(subject=None, errors=None, status=200, semester_id=None):
    semester_id=semester_id or (subject or {}).get("semester_id")
    try:
        context=timetable_service.get_timetable_context(semester_id)
    except mysql.connector.Error:
        if semester_id is not None:
            raise
        context=None
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
    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "all")
    if status_filter not in {"all", "active", "inactive"}:
        status_filter = "all"
    try:
        subjects=(subject_service.list_semester_three_subjects(search,status_filter,semester_id)
                  if semester_id else subject_service.list_semester_three_subjects(search,status_filter))
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not list subjects: %s", exc)
        flash("Subjects could not be loaded. Please try again.", "error")
        subjects = []
    programmes=[]
    for item in contexts:
        if not any(programme["code"]==item["course_code"] for programme in programmes):
            programmes.append({"code":item["course_code"],"name":item["course_name"]})
    semester_options=[item for item in contexts if context and item["course_code"]==context["course_code"]]
    return render_template("admin/subjects/list.html",subjects=subjects,search=search,status_filter=status_filter,
                           context=context,programmes=programmes,semester_options=semester_options)


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
    semester = (timetable_service.get_timetable_context(semester_id)
                if semester_id else subject_service.get_mca_semester_three())
    if semester is None:
        if semester_id is not None:
            abort(404)
        flash("The default programme and semester are not configured.", "error")
        return render_subject_form(data,status=503)
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
    is_active = request.form.get("is_active") == "1"
    try:
        subject_service.set_subject_active(subject_id, is_active)
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not change subject status: %s", exc)
        flash("Subject status could not be changed.", "error")
        return redirect(url_for("admin_subjects.subject_list",**({"semester_id":semester_id} if semester_id else {})))
    flash("Subject activated." if is_active else "Subject deactivated.", "success")
    return redirect(url_for("admin_subjects.subject_list",**({"semester_id":semester_id} if semester_id else {})))

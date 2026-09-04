import mysql.connector
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from decorators.auth import role_required
from services import programme_service


admin_programmes_bp = Blueprint("admin_programmes", __name__, url_prefix="/admin/programmes")


def _render_form(programme=None, errors=None, status=200):
    return render_template(
        "admin/programmes/form.html", programme=programme or {}, errors=errors or {},
    ), status


@admin_programmes_bp.get("")
@role_required("ADMIN")
def programme_list():
    programmes = programme_service.list_programmes()
    return render_template("admin/programmes/list.html", programmes=programmes)


@admin_programmes_bp.route("/add", methods=["GET", "POST"])
@role_required("ADMIN")
def add_programme():
    if request.method == "GET":
        return _render_form()
    data = programme_service.normalize_programme_data(request.form)
    errors = programme_service.validate_programme_data(data)
    if errors:
        return _render_form(data, errors, 400)
    try:
        programme_service.create_programme(data)
    except mysql.connector.IntegrityError:
        errors["code"] = "This programme code is already in use."
        return _render_form(data, errors, 409)
    flash("Programme added successfully.", "success")
    return redirect(url_for("admin_programmes.programme_list"))


@admin_programmes_bp.route("/<int:programme_id>/edit", methods=["GET", "POST"])
@role_required("ADMIN")
def edit_programme(programme_id):
    programme = programme_service.get_programme(programme_id)
    if programme is None:
        abort(404)
    if request.method == "GET":
        return _render_form(programme)
    data = programme_service.normalize_programme_data(request.form)
    errors = programme_service.validate_programme_data(data)
    if data["total_semesters"] is not None and data["total_semesters"] < int(programme["highest_configured_semester"] or 0):
        errors["total_semesters"] = (
            f"Semester {programme['highest_configured_semester']} already exists. "
            "Archive semester groups before reducing this value."
        )
    if errors:
        data.update(id=programme_id, original_code=programme["code"])
        return _render_form(data, errors, 400)
    try:
        programme_service.update_programme(programme_id, data)
    except mysql.connector.IntegrityError:
        errors["code"] = "This programme code is already in use."
        data.update(id=programme_id, original_code=programme["code"])
        return _render_form(data, errors, 409)
    flash("Programme updated. Existing academic records remain connected.", "success")
    return redirect(url_for("admin_programmes.programme_list"))


@admin_programmes_bp.post("/<int:programme_id>/status")
@role_required("ADMIN")
def change_programme_status(programme_id):
    if programme_service.get_programme(programme_id) is None:
        abort(404)
    is_active = request.form.get("is_active") == "1"
    programme_service.set_programme_active(programme_id, is_active)
    flash("Programme activated." if is_active else "Programme archived. Historical data was preserved.", "success")
    return redirect(url_for("admin_programmes.programme_list"))


@admin_programmes_bp.post("/<int:programme_id>/delete")
@role_required("ADMIN")
def delete_programme(programme_id):
    programme = programme_service.get_programme(programme_id)
    if programme is None:
        abort(404)
    if request.form.get("confirmation", "").strip().upper() != f"DELETE {programme['code']}":
        flash(f"Type DELETE {programme['code']} to confirm permanent deletion.", "error")
        return redirect(url_for("admin_programmes.programme_list"))
    try:
        result = programme_service.delete_unused_programme(programme_id)
    except mysql.connector.IntegrityError:
        result = "in_use"
    if result == "in_use":
        flash("This programme contains academic data and cannot be deleted. Archive it instead.", "error")
    else:
        flash("Unused programme permanently deleted.", "success")
    return redirect(url_for("admin_programmes.programme_list"))


def _load_programme(programme_id):
    programme = programme_service.get_programme(programme_id)
    if programme is None:
        abort(404)
    return programme


def _render_cohort_form(programme, cohort=None, errors=None, status=200):
    return render_template(
        "admin/programmes/cohort_form.html", programme=programme,
        cohort=cohort or {}, errors=errors or {},
    ), status


@admin_programmes_bp.get("/<int:programme_id>/cohorts")
@role_required("ADMIN")
def cohort_list(programme_id):
    programme = _load_programme(programme_id)
    cohorts = programme_service.list_cohorts(programme_id)
    return render_template(
        "admin/programmes/cohort_list.html", programme=programme, cohorts=cohorts,
    )


@admin_programmes_bp.route("/<int:programme_id>/cohorts/add", methods=["GET", "POST"])
@role_required("ADMIN")
def add_cohort(programme_id):
    programme = _load_programme(programme_id)
    if request.method == "GET":
        return _render_cohort_form(programme)
    data = programme_service.normalize_cohort_data(request.form)
    errors = programme_service.validate_cohort_data(data, programme)
    if errors:
        return _render_cohort_form(programme, data, errors, 400)
    try:
        programme_service.create_cohort(programme_id, data)
    except mysql.connector.IntegrityError:
        errors["section"] = "This semester, section and academic year already exist."
        return _render_cohort_form(programme, data, errors, 409)
    flash("Semester group added successfully.", "success")
    return redirect(url_for("admin_programmes.cohort_list", programme_id=programme_id))


@admin_programmes_bp.route("/<int:programme_id>/cohorts/<int:cohort_id>/edit", methods=["GET", "POST"])
@role_required("ADMIN")
def edit_cohort(programme_id, cohort_id):
    programme = _load_programme(programme_id)
    cohort = programme_service.get_cohort(programme_id, cohort_id)
    if cohort is None:
        abort(404)
    if request.method == "GET":
        return _render_cohort_form(programme, cohort)
    data = programme_service.normalize_cohort_data(request.form)
    errors = programme_service.validate_cohort_data(data, programme)
    if errors:
        data["id"] = cohort_id
        return _render_cohort_form(programme, data, errors, 400)
    try:
        programme_service.update_cohort(cohort_id, data)
    except mysql.connector.IntegrityError:
        errors["section"] = "This semester, section and academic year already exist."
        data["id"] = cohort_id
        return _render_cohort_form(programme, data, errors, 409)
    flash("Semester group updated. Connected records remain attached to it.", "success")
    return redirect(url_for("admin_programmes.cohort_list", programme_id=programme_id))


@admin_programmes_bp.post("/<int:programme_id>/cohorts/<int:cohort_id>/status")
@role_required("ADMIN")
def change_cohort_status(programme_id, cohort_id):
    _load_programme(programme_id)
    if programme_service.get_cohort(programme_id, cohort_id) is None:
        abort(404)
    is_active = request.form.get("is_active") == "1"
    programme_service.set_cohort_active(cohort_id, is_active)
    flash("Semester group activated." if is_active else "Semester group archived. Historical data was preserved.", "success")
    return redirect(url_for("admin_programmes.cohort_list", programme_id=programme_id))


@admin_programmes_bp.post("/<int:programme_id>/cohorts/<int:cohort_id>/delete")
@role_required("ADMIN")
def delete_cohort(programme_id, cohort_id):
    programme = _load_programme(programme_id)
    cohort = programme_service.get_cohort(programme_id, cohort_id)
    if cohort is None:
        abort(404)
    phrase = f"DELETE {programme['code']} S{cohort['semester_number']} {cohort['section']} {cohort['academic_year']}"
    if request.form.get("confirmation", "").strip().upper() != phrase.upper():
        flash(f"Type {phrase} to confirm permanent deletion.", "error")
        return redirect(url_for("admin_programmes.cohort_list", programme_id=programme_id))
    try:
        result = programme_service.delete_unused_cohort(cohort_id)
    except mysql.connector.IntegrityError:
        result = "in_use"
    if result == "in_use":
        flash("This semester group contains academic data and cannot be deleted. Archive it instead.", "error")
    else:
        flash("Unused semester group permanently deleted.", "success")
    return redirect(url_for("admin_programmes.cohort_list", programme_id=programme_id))

import mysql.connector
from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from decorators.auth import role_required
from services import academic_context_service, correction_service


correction_requests_bp = Blueprint("correction_requests", __name__)


@correction_requests_bp.route("/student/corrections", methods=["GET", "POST"])
@role_required("STUDENT")
def student_requests():
    errors = {}
    form_data = {}
    if request.method == "POST":
        form_data = correction_service.normalize_request_data(request.form)
        errors = correction_service.validate_request_data(form_data)
        if not errors:
            try:
                result = correction_service.create_request(session["user_id"], form_data)
            except mysql.connector.IntegrityError:
                result = "duplicate"
            if result == "not_found":
                abort(404)
            if result == "duplicate":
                errors["attendance_record_id"] = "A correction request already exists for this attendance record."
            else:
                flash("Attendance correction request submitted.", "success")
                return redirect(url_for("correction_requests.student_requests"))

    records = correction_service.list_student_records(session["user_id"])
    requests = correction_service.list_student_requests(session["user_id"])
    return render_template(
        "student/corrections.html", records=records, requests=requests,
        statuses=correction_service.REQUESTABLE_STATUSES, errors=errors, form_data=form_data,
    ), 400 if errors else 200


@correction_requests_bp.get("/corrections")
@role_required("ADMIN", "FACULTY")
def review_list():
    selected_status = request.args.get("status", "PENDING").strip().upper()
    if selected_status not in ("PENDING", "APPROVED", "REJECTED"):
        selected_status = "PENDING"
    context = None
    selector = {"programmes": [], "academic_years": [], "semesters": [], "sections": []}
    if session["role"] == "ADMIN":
        contexts = academic_context_service.list_active_contexts()
        semester_id = request.args.get("semester_id", type=int)
        context = academic_context_service.resolve_context(
            contexts, semester_id=semester_id,
            programme=request.args.get("programme", ""),
            academic_year=request.args.get("academic_year", ""),
            semester=request.args.get("semester", type=int),
            section=request.args.get("section", ""),
        )
        if context is None and (semester_id is not None or request.args.get("programme")):
            abort(404)
        selector = academic_context_service.build_selector_options(contexts, context)
        requests = correction_service.list_review_requests(
            session["user_id"], session["role"], selected_status, context["id"]
        ) if context else []
    else:
        requests = correction_service.list_review_requests(
            session["user_id"], session["role"], selected_status
        )
    return render_template(
        "corrections/review_list.html", requests=requests,
        selected_status=selected_status, dashboard_endpoint=_dashboard_endpoint(),
        context=context, selector=selector,
    )


@correction_requests_bp.post("/corrections/<int:request_id>/review")
@role_required("ADMIN", "FACULTY")
def review(request_id):
    semester_id = request.form.get("semester_id", type=int)
    selected_status = request.form.get("status", "PENDING").strip().upper()
    redirect_args = {"status": selected_status}
    if semester_id is not None:
        redirect_args["semester_id"] = semester_id
    if session["role"] == "ADMIN":
        if semester_id is None or academic_context_service.get_active_context(semester_id) is None:
            abort(404)
    data = correction_service.normalize_review_data(request.form)
    errors = correction_service.validate_review_data(data)
    if errors:
        flash(next(iter(errors.values())), "error")
        return redirect(url_for("correction_requests.review_list", **redirect_args))
    if session["role"] == "ADMIN":
        result = correction_service.review_request(
            request_id, session["user_id"], session["role"], data, semester_id
        )
    else:
        result = correction_service.review_request(
            request_id, session["user_id"], session["role"], data
        )
    if result == "not_found":
        abort(404)
    if result == "forbidden":
        abort(403)
    if result == "already_reviewed":
        flash("This correction request has already been reviewed.", "error")
    elif result == "approved":
        flash("Correction approved and attendance updated.", "success")
    else:
        flash("Correction request rejected.", "success")
    return redirect(url_for("correction_requests.review_list", **redirect_args))


def _dashboard_endpoint():
    return "dashboard.admin_dashboard" if session["role"] == "ADMIN" else "dashboard.faculty_dashboard"

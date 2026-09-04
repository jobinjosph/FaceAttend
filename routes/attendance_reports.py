import csv
import io

from flask import Blueprint, Response, abort, render_template, request, session

from decorators.auth import role_required
from services import pdf_service, report_service, timetable_service


attendance_reports_bp = Blueprint("attendance_reports", __name__, url_prefix="/reports/attendance")


@attendance_reports_bp.get("")
@role_required("ADMIN", "FACULTY")
def attendance_report():
    filters, errors = report_service.normalize_cohort_filters(request.args)
    context, programmes, semester_options = _load_admin_context(filters)
    report = report_service.get_cohort_report(session["user_id"], session["role"], filters)
    if report is None:
        return render_template("reports/report_unavailable.html"), 404
    return render_template(
        "reports/attendance_report.html", report=report, filters=filters, errors=errors,
        dashboard_endpoint=_dashboard_endpoint(),
        month_options=report_service.get_month_options(filters),
        context=context, programmes=programmes, semester_options=semester_options,
    ), 400 if errors else 200


@attendance_reports_bp.get("/export.csv")
@role_required("ADMIN", "FACULTY")
def export_csv():
    report, _ = _load_export_report()
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["FaceAttend attendance report"])
    writer.writerow(["Scope", report["faculty"]["full_name"] if report["faculty"] else "All faculty"])
    writer.writerow(["Attendance percentage", f'{report["summary"]["percentage"]}%'])
    writer.writerow([])
    writer.writerow([
        "Date", "Period", "Register number", "Student", "Subject code", "Subject",
        "Faculty", "Status", "Entry", "Exit", "Duration", "Method",
    ])
    for row in report["history"]:
        writer.writerow([
            row["session_date"], row["period_number"], row["register_number"],
            row["student_name"], row["subject_code"], row["subject_name"],
            row["faculty_name"], row["status"], _time_text(row.get("first_entry")),
            _time_text(row.get("last_exit")), row["duration_label"],
            row.get("marking_method") or "",
        ])
    return Response(
        output.getvalue(), mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=faceattend-cohort-attendance.csv"},
    )


@attendance_reports_bp.get("/export.pdf")
@role_required("ADMIN", "FACULTY")
def export_pdf():
    report, _ = _load_export_report()
    summary = report["summary"]
    scope = report["faculty"]["full_name"] if report["faculty"] else "All faculty"
    lines = [
        f"Scope: {scope}",
        f"Attendance: {summary['percentage']}% ({summary['attended']} of {summary['total']})",
        f"Students below {int(report['threshold'])}%: {report['low_attendance_count']}", "",
        "Date | Student | Subject | Status | Entry | Exit | Duration",
    ]
    for row in report["history"]:
        lines.append(
            f"{row['session_date']} | {row['register_number']} | {row['subject_code']} | "
            f"{row['status']} | {_time_text(row.get('first_entry'))} | "
            f"{_time_text(row.get('last_exit'))} | {row['duration_label']}"
        )
    document = pdf_service.create_text_pdf("FaceAttend Cohort Attendance Report", lines)
    return Response(
        document, mimetype="application/pdf",
        headers={"Content-Disposition": "attachment; filename=faceattend-cohort-attendance.pdf"},
    )


def _load_export_report():
    filters, errors = report_service.normalize_cohort_filters(request.args)
    if errors:
        abort(400)
    if session["role"] == "ADMIN" and filters.get("semester_id"):
        if timetable_service.get_timetable_context(filters["semester_id"]) is None:
            abort(404)
    report = report_service.get_cohort_report(session["user_id"], session["role"], filters)
    if report is None:
        abort(404)
    return report, filters


def _load_admin_context(filters):
    if session["role"] != "ADMIN":
        return None, [], []
    contexts = timetable_service.list_timetable_contexts()
    semester_id = filters.get("semester_id")
    selected_programme = request.args.get("programme", "").strip().upper()
    selected_semester = request.args.get("semester", type=int)
    if not semester_id and selected_programme:
        matching = [item for item in contexts if item["course_code"] == selected_programme]
        context = next(
            (item for item in matching if item["semester_number"] == selected_semester),
            matching[0] if matching else None,
        )
        semester_id = context["id"] if context else None
        filters["semester_id"] = semester_id
    else:
        context = timetable_service.get_timetable_context(semester_id)
    if semester_id is not None and context is None:
        abort(404)
    if context:
        filters["semester_id"] = context["id"]
    programmes = []
    for item in contexts:
        if not any(programme["code"] == item["course_code"] for programme in programmes):
            programmes.append({"code": item["course_code"], "name": item["course_name"]})
    semester_options = [
        item for item in contexts
        if context and item["course_code"] == context["course_code"]
    ]
    return context, programmes, semester_options


def _dashboard_endpoint():
    return "dashboard.admin_dashboard" if session["role"] == "ADMIN" else "dashboard.faculty_dashboard"


def _time_text(value):
    return value.strftime("%H:%M:%S") if hasattr(value, "strftime") else (str(value) if value else "-")

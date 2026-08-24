import csv
import io

from flask import Blueprint, Response, abort, render_template, request, session

from decorators.auth import role_required
from services import pdf_service, report_service


attendance_reports_bp = Blueprint("attendance_reports", __name__, url_prefix="/reports/attendance")


@attendance_reports_bp.get("")
@role_required("ADMIN", "FACULTY")
def attendance_report():
    filters, errors = report_service.normalize_cohort_filters(request.args)
    report = report_service.get_cohort_report(session["user_id"], session["role"], filters)
    if report is None:
        return render_template("reports/report_unavailable.html"), 404
    return render_template(
        "reports/attendance_report.html", report=report, filters=filters, errors=errors,
        dashboard_endpoint=_dashboard_endpoint(),
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
    report = report_service.get_cohort_report(session["user_id"], session["role"], filters)
    if report is None:
        abort(404)
    return report, filters


def _dashboard_endpoint():
    return "dashboard.admin_dashboard" if session["role"] == "ADMIN" else "dashboard.faculty_dashboard"


def _time_text(value):
    return value.strftime("%H:%M:%S") if hasattr(value, "strftime") else (str(value) if value else "-")

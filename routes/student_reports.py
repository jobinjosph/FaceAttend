import csv
import io

from flask import Blueprint, Response, abort, render_template, request, session

from decorators.auth import role_required
from services import pdf_service, report_service


student_reports_bp = Blueprint("student_reports", __name__, url_prefix="/student/attendance")


@student_reports_bp.get("")
@role_required("STUDENT")
def attendance_report():
    filters, errors = report_service.normalize_filters(request.args)
    report = report_service.get_student_report(session["user_id"], filters)
    if report is None:
        return render_template("student/report_unavailable.html"), 404
    return render_template(
        "student/attendance_report.html", report=report, filters=filters, errors=errors,
        month_options=report_service.get_month_options(filters),
    ), 400 if errors else 200


@student_reports_bp.get("/export.csv")
@role_required("STUDENT")
def export_csv():
    report, filters = _load_export_report()
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["FaceAttend attendance report"])
    writer.writerow(["Student", report["student"]["full_name"]])
    writer.writerow(["Register number", report["student"]["register_number"]])
    writer.writerow(["Attendance percentage", f'{report["summary"]["percentage"]}%'])
    writer.writerow([])
    writer.writerow([
        "Date", "Period", "Subject code", "Subject", "Faculty", "Status",
        "Entry", "Exit", "Duration", "Method",
    ])
    for row in report["history"]:
        writer.writerow([
            row["session_date"], row["period_number"], row["subject_code"],
            row["subject_name"], row["faculty_name"], row["status"],
            row.get("first_entry") or "", row.get("last_exit") or "",
            row["duration_label"], row.get("marking_method") or "",
        ])
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=faceattend-attendance.csv"},
    )


@student_reports_bp.get("/export.pdf")
@role_required("STUDENT")
def export_pdf():
    report, filters = _load_export_report()
    student = report["student"]
    summary = report["summary"]
    lines = [
        f"Student: {student['full_name']}",
        f"Register number: {student['register_number']}",
        f"Course: {student['course_code']} - Semester {student['semester_number']}",
        f"Attendance: {summary['percentage']}% ({summary['attended']} of {summary['total']})",
        "",
        "Date | Period | Subject | Status | Entry | Exit | Duration",
    ]
    for row in report["history"]:
        lines.append(
            f"{row['session_date']} | P{row['period_number']} | {row['subject_code']} | "
            f"{row['status']} | {_time_text(row.get('first_entry'))} | "
            f"{_time_text(row.get('last_exit'))} | {row['duration_label']}"
        )
    document = pdf_service.create_text_pdf("FaceAttend Attendance Report", lines)
    return Response(
        document,
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment; filename=faceattend-attendance.pdf"},
    )


def _load_export_report():
    filters, errors = report_service.normalize_filters(request.args)
    if errors:
        abort(400)
    report = report_service.get_student_report(session["user_id"], filters)
    if report is None:
        abort(404)
    return report, filters


def _time_text(value):
    return value.strftime("%H:%M:%S") if hasattr(value, "strftime") else (str(value) if value else "-")

from flask import Blueprint, render_template

from decorators.auth import role_required


dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.get("/admin")
@role_required("ADMIN")
def admin_dashboard():
    return render_template("admin/dashboard.html")


@dashboard_bp.get("/faculty")
@role_required("FACULTY")
def faculty_dashboard():
    return render_template("faculty/dashboard.html")


@dashboard_bp.get("/student")
@role_required("STUDENT")
def student_dashboard():
    return render_template("student/dashboard.html")

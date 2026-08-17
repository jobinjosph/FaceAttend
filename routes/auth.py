import mysql.connector
from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for

from services.auth_service import find_user_by_email, verify_password


auth_bp = Blueprint("auth", __name__)

ROLE_DASHBOARDS = {
    "ADMIN": "dashboard.admin_dashboard",
    "FACULTY": "dashboard.faculty_dashboard",
    "STUDENT": "dashboard.student_dashboard",
}


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        endpoint = ROLE_DASHBOARDS.get(session.get("role"))
        if endpoint:
            return redirect(url_for(endpoint))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter both email and password.", "error")
            return render_template("auth/login.html", email=email), 400

        try:
            user = find_user_by_email(email)
        except mysql.connector.Error as exc:
            current_app.logger.error("Login database error: %s", exc)
            flash("Login is temporarily unavailable. Please try again later.", "error")
            return render_template("auth/login.html", email=email), 503

        if not user or not verify_password(user["password_hash"], password):
            flash("Incorrect email or password.", "error")
            return render_template("auth/login.html", email=email), 401

        if not user["is_active"]:
            flash("This account is inactive. Contact an administrator.", "error")
            return render_template("auth/login.html", email=email), 403

        endpoint = ROLE_DASHBOARDS.get(user["role"])
        if endpoint is None:
            flash("This account has an unsupported role.", "error")
            return render_template("auth/login.html", email=email), 403

        session.clear()
        session["user_id"] = user["id"]
        session["full_name"] = user["full_name"]
        session["role"] = user["role"]

        return redirect(url_for(endpoint))

    return render_template("auth/login.html")


@auth_bp.post("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("main.home"))

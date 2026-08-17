from flask import Blueprint, jsonify, render_template

from db import database_health

main_bp = Blueprint("main", __name__)


@main_bp.get("/")
def home():
    return render_template("home.html")


@main_bp.get("/health")
def health():
    return jsonify(
        {
            "application": "FaceAttend",
            "status": "ok",
        }
    )


@main_bp.get("/health/database")
def database_status():
    ok, message = database_health()

    return (
        jsonify(
            {
                "database": "ok" if ok else "error",
                "message": message,
            }
        ),
        200 if ok else 503,
    )

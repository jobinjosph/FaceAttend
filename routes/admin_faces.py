import mysql.connector
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from decorators.auth import role_required
from services import face_service, student_service


admin_faces_bp = Blueprint("admin_faces", __name__, url_prefix="/admin/students")


@admin_faces_bp.route("/<int:student_id>/face", methods=["GET", "POST"])
@role_required("ADMIN")
def register_face(student_id):
    student = student_service.get_student(student_id)
    if student is None:
        abort(404)
    registration = face_service.get_registration(student_id)
    if request.method == "POST":
        try:
            samples = face_service.parse_samples(request.form.get("samples_json"))
            embedding = face_service.create_embedding(samples)
            face_service.save_registration(student_id, embedding, len(samples))
        except face_service.FaceSampleError as exc:
            flash(str(exc), "error")
            return render_template(
                "admin/students/face.html", student=student,
                registration=registration, required_samples=face_service.REQUIRED_SAMPLES,
            ), 400
        except mysql.connector.Error as exc:
            current_app.logger.error("Could not save face registration: %s", exc)
            flash("Face registration could not be saved.", "error")
            return redirect(url_for("admin_faces.register_face", student_id=student_id))
        flash("Student face registered successfully.", "success")
        return redirect(url_for("admin_faces.register_face", student_id=student_id))
    return render_template(
        "admin/students/face.html", student=student,
        registration=registration, required_samples=face_service.REQUIRED_SAMPLES,
    )


@admin_faces_bp.post("/<int:student_id>/face/remove")
@role_required("ADMIN")
def remove_face(student_id):
    if student_service.get_student(student_id) is None:
        abort(404)
    try:
        face_service.remove_registration(student_id)
    except mysql.connector.Error as exc:
        current_app.logger.error("Could not remove face registration: %s", exc)
        flash("Face registration could not be removed.", "error")
    else:
        flash("Student face registration removed.", "success")
    return redirect(url_for("admin_faces.register_face", student_id=student_id))

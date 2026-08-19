import base64
import json
from binascii import Error as Base64Error

import cv2
import numpy as np

from db import get_db_connection


MODEL_NAME = "opencv-haar-hist-v1"
REQUIRED_SAMPLES = 3
MAX_IMAGE_BYTES = 2 * 1024 * 1024
MIN_FACE_SIZE = 80
MIN_BLUR_SCORE = 35.0


class FaceSampleError(ValueError):
    pass


def parse_samples(value):
    try:
        samples = json.loads(value or "[]")
    except (TypeError, json.JSONDecodeError) as exc:
        raise FaceSampleError("Captured face samples are invalid.") from exc
    if not isinstance(samples, list) or len(samples) != REQUIRED_SAMPLES:
        raise FaceSampleError(f"Capture exactly {REQUIRED_SAMPLES} face samples.")
    if not all(isinstance(sample, str) for sample in samples):
        raise FaceSampleError("Captured face samples are invalid.")
    return samples


def create_embedding(samples):
    detector = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    descriptors = []
    for sample in samples:
        image = _decode_image(sample)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = detector.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=6, minSize=(MIN_FACE_SIZE, MIN_FACE_SIZE)
        )
        if len(faces) == 0:
            raise FaceSampleError("No face was detected. Face the camera and try again.")
        if len(faces) != 1:
            raise FaceSampleError("Only one person may appear in each sample.")
        x, y, width, height = faces[0]
        face = gray[y : y + height, x : x + width]
        if cv2.Laplacian(face, cv2.CV_64F).var() < MIN_BLUR_SCORE:
            raise FaceSampleError("A captured sample is blurry. Hold still and try again.")
        normalized = cv2.resize(face, (128, 128))
        normalized = cv2.equalizeHist(normalized)
        histogram = cv2.calcHist([normalized], [0], None, [256], [0, 256]).flatten()
        norm = np.linalg.norm(histogram)
        if norm == 0:
            raise FaceSampleError("The face sample could not be processed.")
        descriptors.append(histogram / norm)
    averaged = np.mean(descriptors, axis=0)
    averaged /= np.linalg.norm(averaged)
    return [round(float(value), 8) for value in averaged]


def _decode_image(data_url):
    if not data_url.startswith("data:image/") or ";base64," not in data_url:
        raise FaceSampleError("Captured image format is invalid.")
    encoded = data_url.split(",", 1)[1]
    if len(encoded) > ((MAX_IMAGE_BYTES + 2) // 3) * 4:
        raise FaceSampleError("Each face sample must be smaller than 2 MB.")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (Base64Error, ValueError) as exc:
        raise FaceSampleError("Captured image data is invalid.") from exc
    if not raw or len(raw) > MAX_IMAGE_BYTES:
        raise FaceSampleError("Each face sample must be smaller than 2 MB.")
    image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise FaceSampleError("Captured image could not be decoded.")
    if image.shape[0] * image.shape[1] > 1920 * 1080:
        raise FaceSampleError("Captured image dimensions are too large.")
    return image


def get_registration(student_id):
    connection = get_db_connection(); cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """SELECT id, model_name, sample_count, created_at, updated_at
               FROM face_embeddings WHERE student_id=%s AND model_name=%s""",
            (student_id, MODEL_NAME),
        )
        return cursor.fetchone()
    finally:
        cursor.close(); connection.close()


def save_registration(student_id, embedding, sample_count):
    connection = get_db_connection(); cursor = connection.cursor()
    try:
        cursor.execute(
            """INSERT INTO face_embeddings
               (student_id, model_name, embedding_data, sample_count)
               VALUES (%s,%s,%s,%s)
               ON DUPLICATE KEY UPDATE embedding_data=VALUES(embedding_data),
                   sample_count=VALUES(sample_count), updated_at=CURRENT_TIMESTAMP""",
            (student_id, MODEL_NAME, json.dumps(embedding), sample_count),
        )
        cursor.execute("UPDATE students SET face_registered=TRUE WHERE id=%s", (student_id,))
        connection.commit()
    except Exception:
        connection.rollback(); raise
    finally:
        cursor.close(); connection.close()


def remove_registration(student_id):
    connection = get_db_connection(); cursor = connection.cursor()
    try:
        cursor.execute("DELETE FROM face_embeddings WHERE student_id=%s", (student_id,))
        cursor.execute("UPDATE students SET face_registered=FALSE WHERE id=%s", (student_id,))
        connection.commit()
    except Exception:
        connection.rollback(); raise
    finally:
        cursor.close(); connection.close()

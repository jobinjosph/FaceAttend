import base64
import json
from binascii import Error as Base64Error
from pathlib import Path

import cv2
import numpy as np

from db import get_db_connection


MODEL_NAME = "opencv-yunet-sface-v1"
MODEL_DIR = Path(__file__).resolve().parent.parent / "models" / "face"
YUNET_MODEL_PATH = MODEL_DIR / "face_detection_yunet_2023mar.onnx"
SFACE_MODEL_PATH = MODEL_DIR / "face_recognition_sface_2021dec.onnx"
REQUIRED_SAMPLES = 3
MAX_IMAGE_BYTES = 2 * 1024 * 1024
MIN_FACE_SIZE = 80
MIN_BLUR_SCORE = 35.0
DETECTION_SCORE_THRESHOLD = 0.9
COSINE_MATCH_THRESHOLD = 0.363


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


def parse_probe(value):
    if not isinstance(value, str) or not value:
        raise FaceSampleError("Capture one face sample before recognition.")
    return value


def create_embedding(samples):
    detector, recognizer = _load_models()
    descriptors = []
    for sample in samples:
        image = _decode_image(sample)
        height, width = image.shape[:2]
        detector.setInputSize((width, height))
        _, faces = detector.detect(image)
        if faces is None or len(faces) == 0:
            raise FaceSampleError("No face was detected. Face the camera and try again.")
        if len(faces) != 1:
            raise FaceSampleError("Only one person may appear in each sample.")
        face = np.asarray(faces[0], dtype=np.float32)
        x, y, face_width, face_height = face[:4].astype(int)
        if face_width < MIN_FACE_SIZE or face_height < MIN_FACE_SIZE:
            raise FaceSampleError("Move closer so the face fills the camera guide.")
        x, y = max(0, x), max(0, y)
        crop = image[y : min(height, y + face_height), x : min(width, x + face_width)]
        if crop.size == 0:
            raise FaceSampleError("The detected face could not be processed.")
        gray_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        if cv2.Laplacian(gray_crop, cv2.CV_64F).var() < MIN_BLUR_SCORE:
            raise FaceSampleError("A captured sample is blurry. Hold still and try again.")
        aligned = recognizer.alignCrop(image, face)
        descriptor = np.asarray(recognizer.feature(aligned), dtype=np.float32).flatten()
        norm = np.linalg.norm(descriptor)
        if norm == 0:
            raise FaceSampleError("The face sample could not be processed.")
        descriptors.append(descriptor / norm)
    averaged = np.mean(descriptors, axis=0)
    norm = np.linalg.norm(averaged)
    if norm == 0:
        raise FaceSampleError("The face samples could not be combined.")
    averaged /= norm
    return [round(float(value), 8) for value in averaged]


def _load_models():
    missing = [path.name for path in (YUNET_MODEL_PATH, SFACE_MODEL_PATH) if not path.is_file()]
    if missing:
        raise FaceSampleError(
            "Face recognition models are unavailable. Missing: " + ", ".join(missing)
        )
    try:
        detector = cv2.FaceDetectorYN.create(
            str(YUNET_MODEL_PATH), "", (320, 320), DETECTION_SCORE_THRESHOLD, 0.3, 5000
        )
        recognizer = cv2.FaceRecognizerSF.create(str(SFACE_MODEL_PATH), "")
    except cv2.error as exc:
        raise FaceSampleError("Face recognition models could not be loaded.") from exc
    return detector, recognizer


def cosine_similarity(first, second):
    first_vector = np.asarray(first, dtype=np.float32).flatten()
    second_vector = np.asarray(second, dtype=np.float32).flatten()
    if first_vector.shape != second_vector.shape or first_vector.size == 0:
        raise ValueError("Face embeddings must have the same non-empty shape.")
    denominator = np.linalg.norm(first_vector) * np.linalg.norm(second_vector)
    if denominator == 0:
        raise ValueError("Face embeddings cannot be zero vectors.")
    return float(np.dot(first_vector, second_vector) / denominator)


def is_match(first, second, threshold=COSINE_MATCH_THRESHOLD):
    return cosine_similarity(first, second) >= threshold


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

import json
import numpy as np
import pytest
from services import face_service


@pytest.mark.unit
def test_exactly_three_face_samples_are_required():
    with pytest.raises(face_service.FaceSampleError, match="exactly 3"):
        face_service.parse_samples(json.dumps(["one", "two"]))


@pytest.mark.unit
def test_malformed_sample_json_is_rejected():
    with pytest.raises(face_service.FaceSampleError, match="invalid"):
        face_service.parse_samples("not-json")


@pytest.mark.unit
@pytest.mark.parametrize("value", [json.dumps({"sample": "one"}), json.dumps([1, 2, 3])])
def test_samples_must_be_a_list_of_strings(value):
    with pytest.raises(face_service.FaceSampleError, match="invalid|exactly"):
        face_service.parse_samples(value)


@pytest.mark.unit
def test_invalid_image_data_is_rejected():
    with pytest.raises(face_service.FaceSampleError, match="invalid"):
        face_service._decode_image("data:image/jpeg;base64,not base64")


@pytest.mark.unit
def test_oversized_encoded_image_is_rejected_before_decoding():
    encoded = "A" * ((((face_service.MAX_IMAGE_BYTES + 2) // 3) * 4) + 1)
    with pytest.raises(face_service.FaceSampleError, match="smaller than 2 MB"):
        face_service._decode_image(f"data:image/jpeg;base64,{encoded}")


@pytest.mark.unit
def test_excessive_image_dimensions_are_rejected(monkeypatch):
    monkeypatch.setattr(
        face_service.cv2,
        "imdecode",
        lambda *args: np.zeros((1081, 1920, 3), dtype=np.uint8),
    )
    with pytest.raises(face_service.FaceSampleError, match="dimensions"):
        face_service._decode_image("data:image/jpeg;base64,YQ==")


class Detector:
    def __init__(self, faces): self.faces = faces
    def detectMultiScale(self, *args, **kwargs): return np.array(self.faces)


@pytest.mark.unit
def test_sample_without_face_is_rejected(monkeypatch):
    monkeypatch.setattr(face_service.cv2, "CascadeClassifier", lambda path: Detector([]))
    monkeypatch.setattr(face_service, "_decode_image", lambda sample: np.zeros((200, 200, 3), dtype=np.uint8))
    with pytest.raises(face_service.FaceSampleError, match="No face"):
        face_service.create_embedding(["a", "b", "c"])


@pytest.mark.unit
def test_sample_with_multiple_faces_is_rejected(monkeypatch):
    monkeypatch.setattr(face_service.cv2, "CascadeClassifier", lambda path: Detector([(0,0,100,100),(100,0,100,100)]))
    monkeypatch.setattr(face_service, "_decode_image", lambda sample: np.zeros((220, 220, 3), dtype=np.uint8))
    with pytest.raises(face_service.FaceSampleError, match="Only one"):
        face_service.create_embedding(["a", "b", "c"])


@pytest.mark.unit
def test_blurry_face_sample_is_rejected(monkeypatch):
    monkeypatch.setattr(face_service.cv2, "CascadeClassifier", lambda path: Detector([(25, 25, 150, 150)]))
    monkeypatch.setattr(face_service, "_decode_image", lambda sample: np.zeros((200, 200, 3), dtype=np.uint8))
    with pytest.raises(face_service.FaceSampleError, match="blurry"):
        face_service.create_embedding(["a", "b", "c"])


@pytest.mark.unit
def test_clear_single_face_produces_normalized_descriptor(monkeypatch):
    image=np.random.default_rng(4).integers(0,256,(200,200,3),dtype=np.uint8)
    monkeypatch.setattr(face_service.cv2, "CascadeClassifier", lambda path: Detector([(25,25,150,150)]))
    monkeypatch.setattr(face_service, "_decode_image", lambda sample: image)
    descriptor=face_service.create_embedding(["a","b","c"])
    assert len(descriptor)==256
    assert np.linalg.norm(descriptor)==pytest.approx(1.0,abs=1e-5)


class FakeCursor:
    def __init__(self, fail_on=None, row=None):
        self.calls = []
        self.fail_on = fail_on
        self.row = row
        self.closed = False

    def execute(self, query, params):
        self.calls.append((query, params))
        if len(self.calls) == self.fail_on:
            raise RuntimeError("database write failed")

    def fetchone(self):
        return self.row

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, cursor):
        self.test_cursor = cursor
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self, **kwargs):
        return self.test_cursor

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


@pytest.mark.unit
def test_save_registration_commits_embedding_and_student_flag(monkeypatch):
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    monkeypatch.setattr(face_service, "get_db_connection", lambda: connection)

    face_service.save_registration(7, [0.1, 0.2], 3)

    assert len(cursor.calls) == 2
    assert "INSERT INTO face_embeddings" in cursor.calls[0][0]
    assert cursor.calls[0][1] == (7, face_service.MODEL_NAME, "[0.1, 0.2]", 3)
    assert "face_registered=TRUE" in cursor.calls[1][0]
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert cursor.closed and connection.closed


@pytest.mark.unit
def test_save_registration_rolls_back_if_student_update_fails(monkeypatch):
    cursor = FakeCursor(fail_on=2)
    connection = FakeConnection(cursor)
    monkeypatch.setattr(face_service, "get_db_connection", lambda: connection)

    with pytest.raises(RuntimeError, match="database write failed"):
        face_service.save_registration(7, [0.1], 3)

    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert cursor.closed and connection.closed


@pytest.mark.unit
def test_remove_registration_commits_delete_and_student_flag(monkeypatch):
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    monkeypatch.setattr(face_service, "get_db_connection", lambda: connection)

    face_service.remove_registration(7)

    assert len(cursor.calls) == 2
    assert "DELETE FROM face_embeddings" in cursor.calls[0][0]
    assert "face_registered=FALSE" in cursor.calls[1][0]
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert cursor.closed and connection.closed


@pytest.mark.unit
def test_get_registration_returns_row_and_closes_resources(monkeypatch):
    expected = {"id": 4, "model_name": face_service.MODEL_NAME, "sample_count": 3}
    cursor = FakeCursor(row=expected)
    connection = FakeConnection(cursor)
    monkeypatch.setattr(face_service, "get_db_connection", lambda: connection)

    assert face_service.get_registration(7) == expected
    assert cursor.calls[0][1] == (7, face_service.MODEL_NAME)
    assert cursor.closed and connection.closed

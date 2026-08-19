import json

import pytest

from services import attendance_service


class Cursor:
    def __init__(self, session_row, candidates):
        self.session_row = session_row
        self.candidates = candidates
        self.calls = []
        self.closed = False

    def execute(self, query, params):
        self.calls.append((query, params))

    def fetchone(self):
        return self.session_row

    def fetchall(self):
        return self.candidates

    def close(self):
        self.closed = True


class Connection:
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


def candidate(student_id, embedding, status="NOT_MARKED", first_entry=None):
    return {
        "student_id": student_id,
        "status": status,
        "first_entry": first_entry,
        "register_number": f"25MCA{student_id:02d}",
        "full_name": f"Student {student_id}",
        "embedding_data": json.dumps(embedding),
    }


def setup_database(monkeypatch, session_row, candidates):
    cursor = Cursor(session_row, candidates)
    connection = Connection(cursor)
    monkeypatch.setattr(attendance_service, "get_db_connection", lambda: connection)
    return connection, cursor


@pytest.mark.unit
def test_face_match_atomically_marks_present_and_creates_entry_event(monkeypatch):
    connection, cursor = setup_database(
        monkeypatch,
        {"status": "ACTIVE"},
        [candidate(7, [1.0, 0.0, 0.0]), candidate(8, [0.0, 1.0, 0.0])],
    )

    result = attendance_service.recognize_and_mark(3, 4, [1.0, 0.0, 0.0])

    assert result["result"] == "matched"
    assert result["student"]["id"] == 7
    assert "marking_method='FACE'" in cursor.calls[2][0]
    assert "INSERT INTO attendance_events" in cursor.calls[3][0]
    assert connection.commits == 1 and connection.rollbacks == 0
    assert cursor.closed and connection.closed


@pytest.mark.unit
def test_unknown_face_does_not_write_attendance(monkeypatch):
    connection, cursor = setup_database(
        monkeypatch, {"status": "ACTIVE"}, [candidate(7, [0.0, 1.0, 0.0])]
    )
    result = attendance_service.recognize_and_mark(3, 4, [1.0, 0.0, 0.0])
    assert result["result"] == "unknown"
    assert len(cursor.calls) == 2
    assert connection.commits == 0 and connection.rollbacks == 1


@pytest.mark.unit
def test_duplicate_face_does_not_create_second_event(monkeypatch):
    connection, cursor = setup_database(
        monkeypatch,
        {"status": "ACTIVE"},
        [candidate(7, [1.0, 0.0], status="PRESENT", first_entry="2026-08-20 10:01")],
    )
    result = attendance_service.recognize_and_mark(3, 4, [1.0, 0.0])
    assert result["result"] == "duplicate"
    assert len(cursor.calls) == 2
    assert connection.commits == 0 and connection.rollbacks == 1


@pytest.mark.unit
def test_similarly_ranked_faces_are_rejected_as_ambiguous(monkeypatch):
    connection, cursor = setup_database(
        monkeypatch,
        {"status": "ACTIVE"},
        [candidate(7, [1.0, 0.0]), candidate(8, [0.999, 0.045])],
    )
    result = attendance_service.recognize_and_mark(3, 4, [1.0, 0.0])
    assert result["result"] == "ambiguous"
    assert len(cursor.calls) == 2
    assert connection.commits == 0 and connection.rollbacks == 1


@pytest.mark.unit
@pytest.mark.parametrize(
    "session_row,expected",
    [(None, "not_found"), ({"status": "REVIEW"}, "locked")],
)
def test_face_attendance_requires_owned_active_session(monkeypatch, session_row, expected):
    connection, cursor = setup_database(monkeypatch, session_row, [])
    result = attendance_service.recognize_and_mark(3, 4, [1.0])
    assert result["result"] == expected
    assert len(cursor.calls) == 1
    assert connection.rollbacks == 1


@pytest.mark.unit
def test_no_registered_roster_students_is_reported(monkeypatch):
    connection, cursor = setup_database(monkeypatch, {"status": "ACTIVE"}, [])
    result = attendance_service.recognize_and_mark(3, 4, [1.0])
    assert result["result"] == "no_registered"
    assert len(cursor.calls) == 2
    assert connection.rollbacks == 1


@pytest.mark.unit
def test_embedding_deserialization_accepts_mysql_json_and_lists():
    assert attendance_service._deserialize_embedding("[0.1, 0.2]") == [0.1, 0.2]
    assert attendance_service._deserialize_embedding([0.1]) == [0.1]
    with pytest.raises(ValueError):
        attendance_service._deserialize_embedding({"invalid": True})

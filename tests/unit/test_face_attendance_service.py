import json
from datetime import datetime

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


def candidate(
    student_id, embedding, status="NOT_MARKED", first_entry=None,
    last_exit=None, total_present_seconds=0,
):
    return {
        "student_id": student_id,
        "status": status,
        "first_entry": first_entry,
        "last_exit": last_exit,
        "total_present_seconds": total_present_seconds,
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

    assert result["result"] == "entry_recorded"
    assert result["event_type"] == "ENTRY"
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
    assert result["result"] == "duplicate_entry"
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
def test_face_exit_records_duration_and_marks_early_departure(monkeypatch):
    entry_time = datetime(2026, 8, 20, 10, 2)
    exit_time = datetime(2026, 8, 20, 10, 42)
    connection, cursor = setup_database(
        monkeypatch,
        {
            "status": "ACTIVE",
            "scheduled_start_at": datetime(2026, 8, 20, 10, 0),
            "scheduled_end_at": datetime(2026, 8, 20, 10, 50),
        },
        [candidate(7, [1.0, 0.0], status="PRESENT", first_entry=entry_time)],
    )

    result = attendance_service.recognize_and_mark(
        3, 4, [1.0, 0.0], mode="EXIT", now=exit_time
    )

    assert result["result"] == "exit_recorded"
    assert result["event_type"] == "EXIT"
    assert result["duration_seconds"] == 40 * 60
    assert result["status"] == "LEFT_EARLY"
    assert "total_present_seconds=%s" in cursor.calls[2][0]
    assert cursor.calls[3][1][2] == "EXIT"
    assert connection.commits == 1 and connection.rollbacks == 0


@pytest.mark.unit
def test_face_exit_requires_an_entry(monkeypatch):
    connection, cursor = setup_database(
        monkeypatch, {"status": "ACTIVE"}, [candidate(7, [1.0, 0.0])]
    )
    result = attendance_service.recognize_and_mark(
        3, 4, [1.0, 0.0], mode="EXIT"
    )
    assert result["result"] == "entry_required"
    assert len(cursor.calls) == 2
    assert connection.rollbacks == 1


@pytest.mark.unit
def test_duplicate_face_exit_does_not_create_second_event(monkeypatch):
    connection, cursor = setup_database(
        monkeypatch,
        {"status": "ACTIVE"},
        [candidate(
            7, [1.0, 0.0], status="PRESENT",
            first_entry="2026-08-20 10:01:00", last_exit="2026-08-20 10:49:00",
            total_present_seconds=2880,
        )],
    )
    result = attendance_service.recognize_and_mark(
        3, 4, [1.0, 0.0], mode="EXIT"
    )
    assert result["result"] == "duplicate_exit"
    assert result["duration_seconds"] == 2880
    assert len(cursor.calls) == 2
    assert connection.rollbacks == 1


@pytest.mark.unit
def test_late_entry_and_normal_exit_status_calculation():
    start = datetime(2026, 8, 20, 10, 0)
    end = datetime(2026, 8, 20, 10, 50)
    assert attendance_service._entry_status(datetime(2026, 8, 20, 10, 11), start) == "LATE"
    assert attendance_service._entry_status(datetime(2026, 8, 20, 10, 10), start) == "PRESENT"
    assert attendance_service._exit_status("LATE", datetime(2026, 8, 20, 10, 46), end) == "LATE"


@pytest.mark.unit
def test_invalid_face_attendance_mode_is_rejected_before_database_access(monkeypatch):
    monkeypatch.setattr(
        attendance_service, "get_db_connection",
        lambda: (_ for _ in ()).throw(AssertionError("database should not be opened")),
    )
    assert attendance_service.recognize_and_mark(3, 4, [1.0], "invalid") == {
        "result": "invalid_mode"
    }


@pytest.mark.unit
def test_embedding_deserialization_accepts_mysql_json_and_lists():
    assert attendance_service._deserialize_embedding("[0.1, 0.2]") == [0.1, 0.2]
    assert attendance_service._deserialize_embedding([0.1]) == [0.1]
    with pytest.raises(ValueError):
        attendance_service._deserialize_embedding({"invalid": True})

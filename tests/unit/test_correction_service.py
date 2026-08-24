from pathlib import Path

import pytest

from services import correction_service


@pytest.mark.unit
def test_correction_request_is_normalized_and_validated():
    data = correction_service.normalize_request_data(
        {"attendance_record_id": " 8 ", "requested_status": " present ", "reason": " Face   failed "}
    )
    assert data == {"attendance_record_id": 8, "requested_status": "PRESENT", "reason": "Face failed"}
    assert correction_service.validate_request_data(data) == {}


@pytest.mark.unit
def test_invalid_correction_request_returns_all_field_errors():
    data = {"attendance_record_id": None, "requested_status": "WRONG", "reason": ""}
    assert set(correction_service.validate_request_data(data)) == {
        "attendance_record_id", "requested_status", "reason"
    }


@pytest.mark.unit
def test_rejection_requires_a_reviewer_comment():
    assert correction_service.validate_review_data(
        {"decision": "REJECT", "comment": ""}
    )["comment"] == "Add a comment explaining the rejection."
    assert correction_service.validate_review_data(
        {"decision": "APPROVE", "comment": ""}
    ) == {}


@pytest.mark.unit
def test_correction_migration_has_audit_and_duplicate_constraints():
    sql = (Path(__file__).parents[2] / "database/migrations/014_create_attendance_correction_requests.sql").read_text()
    assert "attendance_record_id BIGINT UNSIGNED NOT NULL UNIQUE" in sql
    assert "reviewed_by_user_id" in sql
    assert "reviewed_at" in sql
    assert "FOREIGN KEY (attendance_record_id)" in sql


class FakeCursor:
    def __init__(self, fetches):
        self.fetches = iter(fetches)
        self.calls = []

    def execute(self, query, params=()):
        self.calls.append((" ".join(query.split()), params))

    def fetchone(self):
        return next(self.fetches)

    def close(self):
        pass


class FakeConnection:
    def __init__(self, cursor):
        self.fake_cursor = cursor
        self.committed = False
        self.rolled_back = False

    def cursor(self, dictionary=False):
        return self.fake_cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        pass


@pytest.mark.unit
def test_student_can_create_only_owned_confirmed_record_request(monkeypatch):
    cursor = FakeCursor([{"id": 8, "student_id": 3}, None])
    connection = FakeConnection(cursor)
    monkeypatch.setattr(correction_service, "get_db_connection", lambda: connection)

    result = correction_service.create_request(
        9, {"attendance_record_id": 8, "requested_status": "PRESENT", "reason": "Face failed"}
    )

    assert result == "created" and connection.committed
    assert "st.user_id=%s" in cursor.calls[0][0]
    assert "ats.status='CONFIRMED'" in cursor.calls[0][0]
    assert cursor.calls[-1][1] == (8, 3, "PRESENT", "Face failed")


@pytest.mark.unit
def test_faculty_cannot_review_another_facultys_request(monkeypatch):
    correction = {
        "id": 4, "attendance_record_id": 8, "requested_status": "PRESENT",
        "reason": "Face failed", "status": "PENDING", "faculty_user_id": 22,
        "session_date": "2026-08-25", "scheduled_start": "10:00:00",
    }
    cursor = FakeCursor([correction])
    connection = FakeConnection(cursor)
    monkeypatch.setattr(correction_service, "get_db_connection", lambda: connection)

    result = correction_service.review_request(
        4, 99, "FACULTY", {"decision": "APPROVE", "comment": ""}
    )

    assert result == "forbidden"
    assert connection.rolled_back and not connection.committed
    assert len(cursor.calls) == 1


@pytest.mark.unit
def test_approval_updates_record_and_audit_in_one_transaction(monkeypatch):
    correction = {
        "id": 4, "attendance_record_id": 8, "requested_status": "PRESENT",
        "reason": "Face failed", "status": "PENDING", "faculty_user_id": 22,
        "session_date": "2026-08-25", "scheduled_start": "10:00:00",
    }
    cursor = FakeCursor([correction])
    connection = FakeConnection(cursor)
    monkeypatch.setattr(correction_service, "get_db_connection", lambda: connection)

    result = correction_service.review_request(
        4, 22, "FACULTY", {"decision": "APPROVE", "comment": "Verified in class"}
    )

    assert result == "approved" and connection.committed
    assert "marking_method='ADMIN_CORRECTION'" in cursor.calls[1][0]
    assert "teacher_override=TRUE" in cursor.calls[1][0]
    assert cursor.calls[2][1] == ("APPROVED", 22, "Verified in class", 4)

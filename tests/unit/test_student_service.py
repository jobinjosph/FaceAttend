import pytest
from pathlib import Path

from services import student_service
from services.student_service import (
    normalize_register_number,
    normalize_student_data,
    validate_student_data,
)


@pytest.mark.unit
def test_register_number_is_normalized():
    assert normalize_register_number(" 23 mca 104 ") == "23MCA104"


@pytest.mark.unit
def test_student_data_is_trimmed_and_normalized():
    data = normalize_student_data(
        {
            "register_number": " 23mca104 ",
            "full_name": "  Jobin   Joseph ",
            "email": " JOBIN@EXAMPLE.COM ",
            "password": "Admin@123",
            "course_id": "1",
            "semester_id": "2",
        }
    )

    assert data == {
        "register_number": "23MCA104",
        "full_name": "Jobin Joseph",
        "email": "jobin@example.com",
        "password": "Admin@123",
        "course_id": "1",
        "semester_id": "2",
    }


@pytest.mark.unit
def test_valid_student_data_converts_identifiers_to_integers():
    data = {
        "register_number": "23MCA104",
        "full_name": "Jobin Joseph",
        "email": "jobin@example.com",
        "password": "",
        "course_id": "1",
        "semester_id": "2",
    }

    errors = validate_student_data(data)

    assert errors == {}
    assert data["course_id"] == 1
    assert data["semester_id"] == 2


@pytest.mark.unit
def test_invalid_student_data_returns_field_errors():
    data = {
        "register_number": "",
        "full_name": "",
        "email": "invalid-email",
        "password": "",
        "course_id": "",
        "semester_id": "wrong",
    }

    errors = validate_student_data(data)

    assert set(errors) == {
        "register_number",
        "full_name",
        "email",
        "course_id",
        "semester_id",
    }


@pytest.mark.unit
def test_student_email_and_initial_password_are_required_for_login():
    data = {
        "register_number": "23MCA104",
        "full_name": "Jobin Joseph",
        "email": "",
        "password": "",
        "course_id": "1",
        "semester_id": "2",
    }

    errors = validate_student_data(data, require_password=True)

    assert errors["email"] == "Student login email is required."
    assert errors["password"] == "An initial password is required."


@pytest.mark.unit
def test_optional_edit_password_must_still_be_long_enough_when_supplied():
    data = {
        "register_number": "23MCA104",
        "full_name": "Jobin Joseph",
        "email": "jobin@example.com",
        "password": "short",
        "course_id": "1",
        "semester_id": "2",
    }

    assert validate_student_data(data)["password"] == "Password must be at least 8 characters."


@pytest.mark.unit
def test_student_list_is_limited_to_the_selected_semester_group(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        student_service,
        "_fetch_all",
        lambda query, params=(): captured.update(query=query, params=params) or [],
    )

    student_service.list_students(17)

    assert "WHERE s.semester_id = %s" in captured["query"]
    assert captured["params"] == (17,)


@pytest.mark.unit
def test_new_placement_requires_an_active_programme_and_group(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        student_service,
        "_fetch_one",
        lambda query, params=(): captured.update(query=query, params=params) or {"id": 17},
    )

    assert student_service.active_semester_belongs_to_course(17, 4) is True
    assert "sem.is_active=TRUE" in captured["query"]
    assert "c.is_active=TRUE" in captured["query"]
    assert captured["params"] == (17, 4)


@pytest.mark.unit
def test_placement_history_migration_preserves_the_move_audit_trail():
    sql = (Path(__file__).resolve().parents[2] / "database/migrations/018_create_student_placement_history.sql").read_text()
    assert "student_placement_history" in sql
    assert "from_semester_id" in sql
    assert "to_semester_id" in sql
    assert "moved_by_user_id" in sql
    assert "moved_at" in sql


@pytest.mark.unit
def test_bulk_placement_records_history_and_updates_current_group(monkeypatch):
    class Cursor:
        def __init__(self):
            self.executed = []
            self.history_rows = []
            self.results = iter([{"id": 9, "course_id": 4}, None])

        def execute(self, query, params):
            self.executed.append((query, params))

        def fetchone(self):
            return next(self.results)

        def fetchall(self):
            return [{"id": 7, "semester_id": 2}, {"id": 8, "semester_id": 2}]

        def executemany(self, query, rows):
            self.history_rows = list(rows)

        def close(self):
            pass

    class Connection:
        def __init__(self):
            self.test_cursor = Cursor()
            self.committed = False
            self.rolled_back = False

        def cursor(self, **kwargs):
            return self.test_cursor

        def commit(self):
            self.committed = True

        def rollback(self):
            self.rolled_back = True

        def close(self):
            pass

    connection = Connection()
    monkeypatch.setattr(student_service, "get_db_connection", lambda: connection)

    assert student_service.move_students([7, 8], 2, 9, 1) == 2
    assert connection.committed is True
    assert connection.rolled_back is False
    assert connection.test_cursor.history_rows == [(7, 2, 9, 1), (8, 2, 9, 1)]
    update_query, update_params = connection.test_cursor.executed[-1]
    assert "UPDATE students" in update_query
    assert update_params == (4, 9, 7, 8)


@pytest.mark.unit
def test_placement_history_is_loaded_newest_first(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        student_service,
        "_fetch_all",
        lambda query, params=(): captured.update(query=query, params=params) or [],
    )

    student_service.get_placement_history(7)

    assert "student_placement_history" in captured["query"]
    assert "from_semester_id" in captured["query"]
    assert "to_semester_id" in captured["query"]
    assert "ORDER BY h.moved_at DESC" in captured["query"]
    assert captured["params"] == (7,)


@pytest.mark.unit
def test_bulk_students_are_normalized_and_duplicate_rows_are_rejected():
    rows = [
        {"register_number": " 25mca001 ", "full_name": " Student   One ",
         "email": "ONE@EXAMPLE.COM", "initial_password": "Student123"},
        {"register_number": "25MCA001", "full_name": "Student Two",
         "email": "one@example.com", "initial_password": "short"},
    ]

    prepared, errors = student_service.prepare_bulk_students(rows, 4, 9)

    assert prepared[0]["register_number"] == "25MCA001"
    assert prepared[0]["full_name"] == "Student One"
    assert prepared[0]["email"] == "one@example.com"
    assert prepared[0]["course_id"] == 4
    assert prepared[0]["semester_id"] == 9
    assert len(errors) == 1
    assert "Row 3" in errors[0]
    assert "duplicated in this file" in errors[0]
    assert "at least 8 characters" in errors[0]


@pytest.mark.unit
def test_bulk_student_import_rejects_empty_and_oversized_files():
    assert student_service.prepare_bulk_students([], 1, 2)[1]
    rows = [{"register_number": str(index)} for index in range(3)]
    _, errors = student_service.prepare_bulk_students(rows, 1, 2, maximum_rows=2)
    assert errors == ["Import at most 2 students at a time."]

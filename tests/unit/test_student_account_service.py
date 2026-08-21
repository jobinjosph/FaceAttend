import pytest

from services import student_service


class FakeCursor:
    def __init__(self, insert_ids=()):
        self.insert_ids = iter(insert_ids)
        self.lastrowid = None
        self.calls = []

    def execute(self, query, params=()):
        self.calls.append((" ".join(query.split()), params))
        if query.lstrip().upper().startswith("INSERT"):
            self.lastrowid = next(self.insert_ids)

    def close(self):
        pass


class FakeConnection:
    def __init__(self, cursor):
        self.fake_cursor = cursor
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self, dictionary=False):
        return self.fake_cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def student_data(password="Student@123"):
    return {
        "register_number": "23MCA104",
        "full_name": "Test Student",
        "email": "student@example.com",
        "password": password,
        "course_id": 1,
        "semester_id": 2,
    }


@pytest.mark.unit
def test_create_student_creates_linked_login_in_one_transaction(monkeypatch):
    cursor = FakeCursor((40, 8))
    connection = FakeConnection(cursor)
    monkeypatch.setattr(student_service, "get_db_connection", lambda: connection)
    monkeypatch.setattr(student_service, "hash_password", lambda password: f"hashed:{password}")

    student_id = student_service.create_student(student_data())

    assert student_id == 8
    assert connection.committed is True
    assert cursor.calls[0][1] == (
        "Test Student", "student@example.com", "hashed:Student@123"
    )
    assert "'STUDENT'" in cursor.calls[0][0]
    assert cursor.calls[1][1][0] == 40


@pytest.mark.unit
def test_update_linked_student_keeps_password_when_blank(monkeypatch):
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    monkeypatch.setattr(
        student_service,
        "get_student",
        lambda student_id: {"id": student_id, "user_id": 40, "is_active": True},
    )
    monkeypatch.setattr(student_service, "get_db_connection", lambda: connection)

    student_service.update_student(8, student_data(password=""))

    assert connection.committed is True
    assert "password_hash" not in cursor.calls[0][0]
    assert cursor.calls[0][1] == ("Test Student", "student@example.com", 40)
    assert cursor.calls[1][1][0] == 40


@pytest.mark.unit
def test_student_activation_status_is_synchronized_to_login(monkeypatch):
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    monkeypatch.setattr(
        student_service,
        "get_student",
        lambda student_id: {"id": student_id, "user_id": 40},
    )
    monkeypatch.setattr(student_service, "get_db_connection", lambda: connection)

    student_service.set_student_active(8, False)

    assert connection.committed is True
    assert cursor.calls[0][1] == (False, 8)
    assert cursor.calls[1][1] == (False, 40)

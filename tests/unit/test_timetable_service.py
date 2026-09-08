import pytest

from services import timetable_service
from services.timetable_service import normalize_period_data, validate_period_data


@pytest.mark.unit
def test_period_data_is_normalized():
    assert normalize_period_data({"assignment_id": "2", "day_of_week": "6", "period_number": "4", "start_time": "09:00", "end_time": "09:50"}) == {
        "assignment_id": 2, "day_of_week": 6, "period_number": 4,
        "start_time": "09:00", "end_time": "09:50", "activity_name": "",
    }


@pytest.mark.unit
def test_period_requires_valid_fields():
    errors = validate_period_data(normalize_period_data({}))
    assert set(errors) == {"assignment_id", "day_of_week", "period_number", "start_time", "end_time"}


@pytest.mark.unit
def test_sunday_is_not_a_teaching_day():
    data = {"assignment_id": 1, "day_of_week": 7, "period_number": 1, "start_time": "09:00", "end_time": "10:00", "activity_name": ""}
    assert "day_of_week" in validate_period_data(data)


@pytest.mark.unit
def test_end_time_must_follow_start_time():
    data = {"assignment_id": 1, "day_of_week": 1, "period_number": 1, "start_time": "10:00", "end_time": "09:00", "activity_name": ""}
    assert validate_period_data(data)["end_time"] == "End time must be later than start time."


@pytest.mark.unit
def test_valid_period_has_no_errors():
    data = {"assignment_id": 1, "day_of_week": 1, "period_number": 1, "start_time": "09:00", "end_time": "09:50", "activity_name": ""}
    assert validate_period_data(data) == {}


@pytest.mark.unit
def test_unassigned_activity_is_valid_without_assignment():
    data = {"assignment_id": None, "day_of_week": 6, "period_number": 1, "start_time": "10:00", "end_time": "10:50", "activity_name": "Placement Training"}
    assert validate_period_data(data) == {}


@pytest.mark.unit
@pytest.mark.parametrize(
    ("operation", "expected_params", "scope"),
    [
        (lambda: timetable_service.get_assignment_options(22), (22,), "s.semester_id=%s"),
        (lambda: timetable_service.get_assignment(7, 22), (7, 22), "s.semester_id=%s"),
        (lambda: timetable_service.list_periods(22), (22,), "tp.semester_id=%s"),
    ],
)
def test_timetable_queries_require_explicit_group(monkeypatch, operation, expected_params, scope):
    captured = {}
    monkeypatch.setattr(
        timetable_service, "_fetch_all",
        lambda query, params=(): captured.update(query=query, params=params) or [],
    )
    monkeypatch.setattr(
        timetable_service, "_fetch_one",
        lambda query, params=(): captured.update(query=query, params=params),
    )

    operation()

    assert scope in captured["query"]
    assert "MCA" not in captured["query"]
    assert captured["params"] == expected_params


class FakeCursor:
    def __init__(self, fetch_results):
        self.fetch_results = iter(fetch_results)
        self.executions = []
        self.lastrowid = 41

    def execute(self, query, params=()):
        self.executions.append((" ".join(query.split()), params))

    def fetchone(self):
        return next(self.fetch_results)

    def close(self):
        pass


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        pass


@pytest.mark.unit
def test_write_rechecks_conflicts_after_locking_group_and_faculty(monkeypatch):
    cursor = FakeCursor([(22,), (5,), (99,)])
    connection = FakeConnection(cursor)
    monkeypatch.setattr(timetable_service, "get_db_connection", lambda: connection)
    data = {"day_of_week": 1, "period_number": 1, "start_time": "09:00", "end_time": "09:50", "activity_name": ""}
    assignment = {"semester_id": 22, "subject_id": 4, "faculty_id": 5}

    with pytest.raises(timetable_service.TimetableConflictError) as exc:
        timetable_service.create_period(data, assignment)

    assert exc.value.conflict_type == "semester"
    assert "semesters WHERE id = %s FOR UPDATE" in cursor.executions[0][0]
    assert "faculty WHERE id = %s FOR UPDATE" in cursor.executions[1][0]
    assert "timetable_periods" in cursor.executions[2][0]
    assert connection.rolled_back is True
    assert connection.committed is False


@pytest.mark.unit
def test_write_checks_faculty_across_groups_before_insert(monkeypatch):
    cursor = FakeCursor([(22,), (5,), None, (77,)])
    connection = FakeConnection(cursor)
    monkeypatch.setattr(timetable_service, "get_db_connection", lambda: connection)
    data = {"day_of_week": 2, "period_number": 3, "start_time": "11:00", "end_time": "11:50", "activity_name": ""}
    assignment = {"semester_id": 22, "subject_id": 4, "faculty_id": 5}

    with pytest.raises(timetable_service.TimetableConflictError) as exc:
        timetable_service.create_period(data, assignment)

    assert exc.value.conflict_type == "faculty"
    assert cursor.executions[3][1] == (2, "11:50", "11:00", 5)
    assert connection.rolled_back is True


@pytest.mark.unit
def test_conflict_free_write_commits_after_locked_recheck(monkeypatch):
    cursor = FakeCursor([(22,), (5,), None, None])
    connection = FakeConnection(cursor)
    monkeypatch.setattr(timetable_service, "get_db_connection", lambda: connection)
    data = {"day_of_week": 3, "period_number": 2, "start_time": "10:00", "end_time": "10:50", "activity_name": ""}
    assignment = {"semester_id": 22, "subject_id": 4, "faculty_id": 5}

    period_id = timetable_service.create_period(data, assignment)

    assert period_id == 41
    assert cursor.executions[-1][0].startswith("INSERT INTO timetable_periods")
    assert connection.committed is True
    assert connection.rolled_back is False


@pytest.mark.unit
def test_update_conflict_check_excludes_period_being_edited(monkeypatch):
    cursor = FakeCursor([(22,), (5,), None, (77,)])
    connection = FakeConnection(cursor)
    monkeypatch.setattr(timetable_service, "get_db_connection", lambda: connection)
    data = {"day_of_week": 4, "period_number": 4, "start_time": "13:40", "end_time": "14:30", "activity_name": ""}
    assignment = {"semester_id": 22, "subject_id": 4, "faculty_id": 5}

    with pytest.raises(timetable_service.TimetableConflictError):
        timetable_service.update_period(9, data, assignment)

    assert cursor.executions[2][1] == (4, "14:30", "13:40", 22, 9)
    assert cursor.executions[3][1] == (4, "14:30", "13:40", 5, 9)

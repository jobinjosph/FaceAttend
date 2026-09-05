from datetime import date
import pytest
from services import session_service
from services.session_service import parse_session_date


@pytest.mark.unit
def test_valid_session_date_is_parsed(): assert parse_session_date("2026-08-24") == date(2026, 8, 24)


@pytest.mark.unit
@pytest.mark.parametrize("value", ["", None, "24-08-2026", "2026-99-99"])
def test_invalid_session_date_is_rejected(value): assert parse_session_date(value) is None


@pytest.mark.unit
def test_admin_session_list_is_scoped_to_selected_semester(monkeypatch):
    captured = {}

    def fetch_all(query, params=()):
        captured.update(query=query, params=params)
        return []

    monkeypatch.setattr(session_service, "_fetch_all", fetch_all)
    selected = date(2026, 8, 24)

    session_service.list_sessions(selected, 22)

    assert "ats.semester_id = %s" in captured["query"]
    assert "MCA" not in captured["query"]
    assert captured["params"] == (selected, 22)


@pytest.mark.unit
def test_generation_is_duplicate_safe_and_scoped_to_selected_semester(monkeypatch):
    captured = {}

    class Cursor:
        rowcount = 2

        def execute(self, query, params):
            captured.update(query=query, params=params)

        def close(self):
            pass

    class Connection:
        def cursor(self):
            return Cursor()

        def commit(self):
            captured["committed"] = True

        def rollback(self):
            captured["rolled_back"] = True

        def close(self):
            pass

    monkeypatch.setattr(session_service, "get_db_connection", lambda: Connection())
    selected = date(2026, 8, 24)

    assert session_service.generate_sessions(selected, 22) == 2
    assert "INSERT IGNORE INTO attendance_sessions" in captured["query"]
    assert "tp.semester_id = %s" in captured["query"]
    assert "MCA" not in captured["query"]
    assert captured["params"] == (selected, 1, 22)
    assert captured["committed"] is True

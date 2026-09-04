import pytest

from services import assignment_service
from services.assignment_service import normalize_assignment_data, validate_assignment_data


@pytest.mark.unit
def test_assignment_identifiers_are_converted_to_integers():
    assert normalize_assignment_data({"subject_id": "4", "faculty_id": "9"}) == {
        "subject_id": 4, "faculty_id": 9,
    }


@pytest.mark.unit
def test_invalid_assignment_identifiers_are_rejected():
    data = normalize_assignment_data({"subject_id": "", "faculty_id": "wrong"})
    assert set(validate_assignment_data(data)) == {"subject_id", "faculty_id"}


@pytest.mark.unit
def test_valid_assignment_has_no_errors():
    assert validate_assignment_data({"subject_id": 1, "faculty_id": 2}) == {}


@pytest.mark.unit
def test_assignment_list_is_scoped_to_selected_semester(monkeypatch):
    captured = {}

    def fetch_all(query, params=()):
        captured.update(query=query, params=params)
        return []

    monkeypatch.setattr(assignment_service, "_fetch_all", fetch_all)

    assignment_service.list_assignments(22)

    assert "sem.id = %s" in captured["query"]
    assert captured["params"] == (22, 22)


@pytest.mark.unit
def test_assignment_subject_validation_is_scoped_to_selected_semester(monkeypatch):
    captured = {}

    def fetch_one(query, params=()):
        captured.update(query=query, params=params)
        return {"id": 30}

    monkeypatch.setattr(assignment_service, "_fetch_one", fetch_one)

    assert assignment_service.active_subject_exists(30, 22) is True
    assert "sem.id = %s" in captured["query"]
    assert captured["params"] == (30, 22, 22)

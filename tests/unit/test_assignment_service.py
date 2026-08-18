import pytest

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

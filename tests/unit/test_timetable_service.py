import pytest

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

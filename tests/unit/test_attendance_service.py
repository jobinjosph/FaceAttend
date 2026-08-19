import pytest
from services.attendance_service import (
    normalize_attendance_data, normalize_bulk_attendance,
    validate_attendance_data, validate_bulk_attendance,
)


@pytest.mark.unit
def test_attendance_data_is_normalized():
    assert normalize_attendance_data({"status":"present","notes":"  Arrived   manually "}) == {"status":"PRESENT","notes":"Arrived manually"}


@pytest.mark.unit
@pytest.mark.parametrize("status",["PRESENT","ABSENT","LATE","LEFT_EARLY","NOT_MARKED"])
def test_manual_statuses_are_valid(status): assert validate_attendance_data({"status":status,"notes":""})=={}


@pytest.mark.unit
def test_invalid_status_and_long_notes_are_rejected():
    assert set(validate_attendance_data({"status":"WRONG","notes":"x"*256}))=={"status","notes"}


@pytest.mark.unit
def test_bulk_attendance_is_normalized_by_student_id():
    records=normalize_bulk_attendance({"status_10":"present","notes_10":"  On time ","status_11":"absent","notes_11":""},[10,11])
    assert records=={10:{"status":"PRESENT","notes":"On time"},11:{"status":"ABSENT","notes":""}}
    assert validate_bulk_attendance(records)=={}


@pytest.mark.unit
def test_bulk_validation_identifies_invalid_student_row():
    errors=validate_bulk_attendance({10:{"status":"WRONG","notes":""},11:{"status":"PRESENT","notes":""}})
    assert set(errors)=={10}

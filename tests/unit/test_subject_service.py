import pytest

from services.subject_service import normalize_subject_data, validate_subject_data


@pytest.mark.unit
def test_subject_data_is_normalized():
    assert normalize_subject_data({
        "subject_code": " cc 431 ",
        "subject_name": "  Cloud   Computing ",
        "activity_type": "lecture",
    }) == {
        "subject_code": "CC431",
        "subject_name": "Cloud Computing",
        "activity_type": "LECTURE",
    }


@pytest.mark.unit
def test_subject_requires_code_name_and_valid_type():
    errors = validate_subject_data({
        "subject_code": "", "subject_name": "", "activity_type": "INVALID"
    })
    assert set(errors) == {"subject_code", "subject_name", "activity_type"}


@pytest.mark.unit
@pytest.mark.parametrize("activity_type", ["LECTURE", "THEORY", "PRACTICAL", "PROJECT"])
def test_supported_activity_types_are_valid(activity_type):
    assert validate_subject_data({
        "subject_code": "CC431",
        "subject_name": "Cloud Computing",
        "activity_type": activity_type,
    }) == {}

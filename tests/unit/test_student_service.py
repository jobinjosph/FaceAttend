import pytest

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
            "course_id": "1",
            "semester_id": "2",
        }
    )

    assert data == {
        "register_number": "23MCA104",
        "full_name": "Jobin Joseph",
        "email": "jobin@example.com",
        "course_id": "1",
        "semester_id": "2",
    }


@pytest.mark.unit
def test_valid_student_data_converts_identifiers_to_integers():
    data = {
        "register_number": "23MCA104",
        "full_name": "Jobin Joseph",
        "email": "jobin@example.com",
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
def test_student_email_is_optional():
    data = {
        "register_number": "23MCA104",
        "full_name": "Jobin Joseph",
        "email": "",
        "course_id": "1",
        "semester_id": "2",
    }

    assert validate_student_data(data) == {}

import pytest

from services.faculty_service import (
    normalize_employee_code,
    normalize_faculty_data,
    validate_faculty_data,
)


@pytest.mark.unit
def test_employee_code_is_normalized():
    assert normalize_employee_code(" fc 001 ") == "FC001"


@pytest.mark.unit
def test_faculty_data_is_normalized():
    data = normalize_faculty_data(
        {
            "employee_code": " fc 001 ",
            "full_name": "  Test   Faculty ",
            "email": " FACULTY@EXAMPLE.COM ",
            "password": "FacultyPass123",
        }
    )

    assert data == {
        "employee_code": "FC001",
        "full_name": "Test Faculty",
        "email": "faculty@example.com",
        "password": "FacultyPass123",
    }


@pytest.mark.unit
def test_new_faculty_requires_valid_fields_and_password():
    data = {
        "employee_code": "",
        "full_name": "",
        "email": "wrong-email",
        "password": "short",
    }

    errors = validate_faculty_data(data, require_password=True)

    assert set(errors) == {"employee_code", "full_name", "email", "password"}


@pytest.mark.unit
def test_edit_faculty_allows_blank_password():
    data = {
        "employee_code": "FC001",
        "full_name": "Test Faculty",
        "email": "faculty@example.com",
        "password": "",
    }

    assert validate_faculty_data(data, require_password=False) == {}


@pytest.mark.unit
def test_new_faculty_accepts_secure_valid_data():
    data = {
        "employee_code": "FC001",
        "full_name": "Test Faculty",
        "email": "faculty@example.com",
        "password": "FacultyPass123",
    }

    assert validate_faculty_data(data, require_password=True) == {}

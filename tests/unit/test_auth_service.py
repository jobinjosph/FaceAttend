import pytest

from services.auth_service import hash_password, verify_password


@pytest.mark.unit
def test_password_is_hashed_and_can_be_verified():
    password = "StrongPass123"
    password_hash = hash_password(password)

    assert password_hash != password
    assert verify_password(password_hash, password) is True


@pytest.mark.unit
def test_wrong_password_is_rejected():
    password_hash = hash_password("CorrectPass123")

    assert verify_password(password_hash, "WrongPass123") is False


@pytest.mark.unit
def test_empty_password_values_are_rejected():
    assert verify_password("", "anything") is False
    assert verify_password("hash", "") is False

from datetime import date
import pytest
from services.session_service import parse_session_date


@pytest.mark.unit
def test_valid_session_date_is_parsed(): assert parse_session_date("2026-08-24") == date(2026, 8, 24)


@pytest.mark.unit
@pytest.mark.parametrize("value", ["", None, "24-08-2026", "2026-99-99"])
def test_invalid_session_date_is_rejected(value): assert parse_session_date(value) is None

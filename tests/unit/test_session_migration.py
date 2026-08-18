from pathlib import Path
import pytest


@pytest.mark.unit
def test_session_migration_prevents_duplicate_timetable_date():
    sql=(Path(__file__).resolve().parents[2]/"database"/"migrations"/"011_add_attendance_session_generation_constraint.sql").read_text()
    assert "UNIQUE (timetable_period_id, session_date)" in sql
    assert "idx_session_faculty_date_status" in sql

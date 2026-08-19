from pathlib import Path
import pytest


@pytest.mark.unit
def test_roster_migration_adds_lookup_indexes():
    sql=(Path(__file__).resolve().parents[2]/"database"/"migrations"/"012_add_attendance_roster_indexes.sql").read_text()
    assert "idx_attendance_record_session_status" in sql
    assert "idx_student_semester_active" in sql

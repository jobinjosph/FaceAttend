from pathlib import Path
import pytest


@pytest.mark.unit
def test_timetable_migration_adds_unique_period_and_overlap_indexes():
    sql = (Path(__file__).resolve().parents[2] / "database" / "migrations" / "008_add_timetable_constraints.sql").read_text()
    assert "UNIQUE (semester_id, day_of_week, period_number)" in sql
    assert "idx_timetable_semester_day_time" in sql
    assert "idx_timetable_faculty_day_time" in sql

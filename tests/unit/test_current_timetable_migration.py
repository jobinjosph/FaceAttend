from pathlib import Path
import pytest


@pytest.mark.unit
def test_current_timetable_migration_contains_all_33_periods_and_unassigned_activities():
    sql = (Path(__file__).resolve().parents[2] / "database" / "migrations" / "010_seed_current_mca_semester_three_timetable.sql").read_text()
    assert sql.count("),\n(") == 32
    assert "Placement Training" in sql
    assert "Skill Development Activity" in sql
    assert sql.count("'Library'") == 2
    assert "'ECP434','T04'" in sql
    assert sql.count("'ECP Practical'") == 2

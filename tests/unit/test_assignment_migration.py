from pathlib import Path

import pytest


@pytest.mark.unit
def test_faculty_subject_assignment_migration_has_required_constraints():
    migration = (
        Path(__file__).resolve().parents[2]
        / "database" / "migrations" / "006_create_faculty_subject_assignments.sql"
    ).read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS faculty_subject_assignments" in migration
    assert "UNIQUE (subject_id, faculty_id)" in migration
    assert "FOREIGN KEY (subject_id)" in migration
    assert "FOREIGN KEY (faculty_id)" in migration

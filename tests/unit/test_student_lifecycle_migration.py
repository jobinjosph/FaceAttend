from pathlib import Path

import pytest


@pytest.mark.unit
def test_student_lifecycle_migration_preserves_records_and_adds_audit_history():
    sql = (
        Path(__file__).resolve().parents[2]
        / "database/migrations/020_add_student_lifecycle.sql"
    ).read_text()

    for status in ("ACTIVE", "GRADUATED", "WITHDRAWN", "ARCHIVED"):
        assert status in sql
    assert "student_lifecycle_history" in sql
    assert "previous_status" in sql
    assert "new_status" in sql
    assert "changed_by_user_id" in sql
    assert "DELETE FROM STUDENTS" not in sql.upper()

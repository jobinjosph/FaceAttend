from pathlib import Path

import pytest


@pytest.mark.unit
def test_subject_active_migration_is_present():
    migration = (
        Path(__file__).resolve().parents[2]
        / "database" / "migrations" / "004_add_subject_active.sql"
    ).read_text(encoding="utf-8")
    assert "ALTER TABLE subjects" in migration
    assert "ADD COLUMN is_active" in migration
    assert "DEFAULT TRUE" in migration

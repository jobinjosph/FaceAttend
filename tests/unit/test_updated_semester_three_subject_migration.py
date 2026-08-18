from pathlib import Path

import pytest


@pytest.mark.unit
def test_updated_semester_three_migration_contains_current_subject_list():
    migration = (
        Path(__file__).resolve().parents[2]
        / "database" / "migrations" / "007_update_mca_semester_three_subjects.sql"
    ).read_text(encoding="utf-8")
    expected = [
        "Cloud Computing", "Cloud Computing Practical",
        "Enterprise Computing Project", "Mobile Application Development",
        "Mobile Application Development Practical", "Digital Analytics",
        "Research Methodology", "Ventureship and Startup Management",
    ]
    for subject in expected:
        assert subject in migration
    assert "s.is_active = FALSE" in migration

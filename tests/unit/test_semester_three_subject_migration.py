from pathlib import Path

import pytest


@pytest.mark.unit
def test_semester_three_subject_migration_contains_requested_subjects():
    migration = (
        Path(__file__).resolve().parents[2]
        / "database" / "migrations" / "005_seed_mca_semester_three_subjects.sql"
    ).read_text(encoding="utf-8")

    subjects = [
        "Cloud Computing",
        "Cloud Computing Practical",
        "Digital Analytics",
        "Enterprise Computing Project",
        "Internship Project Presentation",
        "Mobile Application Development",
    ]
    for subject in subjects:
        assert subject in migration

    assert "sem.semester_number = 3" in migration
    assert "c.code = 'MCA'" in migration
    assert "is_active = FALSE" in migration

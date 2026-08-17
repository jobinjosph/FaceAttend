from pathlib import Path

import pytest


MIGRATION_FILE = (
    Path(__file__).resolve().parents[2]
    / "database"
    / "migrations"
    / "002_seed_pg_programmes.sql"
)


@pytest.mark.unit
def test_pg_programme_migration_contains_all_requested_programmes():
    migration = MIGRATION_FILE.read_text(encoding="utf-8")
    programme_names = [
        "MA English Literature",
        "MA Media & Communication",
        "MA Public Policy & International Relations",
        "M.Sc Psychology",
        "M.Sc Clinical Psychology",
        "M.Sc Counselling Psychology",
        "M.Sc Human Resource Development Psychology",
        "Master of Social Work (MSW)",
        "Master of Computer Applications",
        "M.Sc Data Science",
        "M.Sc Cyber Security",
        "M.Sc Physics",
        "M.Sc Applied Statistics & Data Analytics",
        "M.Sc Economics",
        "M.Com Financial Analysis",
        "M.Com International Taxation & Applied Finance",
        "M.Sc Biochemistry",
        "M.Sc Biotechnology",
        "M.Sc Microbiology",
        "M.Sc Forensic Science",
        "M.Sc Bioinformatics",
        "M.Sc Digital Forensics & Information Security",
        "LL.M Constitutional & Administrative Law",
        "LL.M IPR & Technology Law",
    ]

    assert len(programme_names) == 24
    for programme_name in programme_names:
        assert programme_name in migration


@pytest.mark.unit
def test_pg_programme_migration_creates_all_four_semesters():
    migration = MIGRATION_FILE.read_text(encoding="utf-8")

    assert "SELECT 1 AS semester_number" in migration
    assert "UNION ALL SELECT 2" in migration
    assert "UNION ALL SELECT 3" in migration
    assert "UNION ALL SELECT 4" in migration
    assert "'2026-27'" in migration

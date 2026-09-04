from pathlib import Path

import pytest

from services import programme_service


@pytest.mark.unit
def test_programme_data_is_normalized_and_validated():
    data = programme_service.normalize_programme_data(
        {"code": " bca ", "name": " Bachelor   of Computer Applications ", "total_semesters": "6"}
    )
    assert data == {
        "code": "BCA", "name": "Bachelor of Computer Applications", "total_semesters": 6,
    }
    assert programme_service.validate_programme_data(data) == {}


@pytest.mark.unit
def test_invalid_programme_data_returns_all_errors():
    data = programme_service.normalize_programme_data(
        {"code": "!", "name": "", "total_semesters": "20"}
    )
    assert set(programme_service.validate_programme_data(data)) == {
        "code", "name", "total_semesters",
    }


@pytest.mark.unit
def test_used_programme_cannot_be_permanently_deleted(monkeypatch):
    monkeypatch.setattr(
        programme_service,
        "get_programme_impact",
        lambda programme_id: {
            "id": programme_id, "code": "BCA", "cohorts": 1, "students": 0,
            "subjects": 0, "timetable_periods": 0, "attendance_sessions": 0,
            "attendance_records": 0,
        },
    )
    monkeypatch.setattr(programme_service, "_write", lambda *args: pytest.fail("delete must not run"))

    assert programme_service.delete_unused_programme(8) == "in_use"


@pytest.mark.unit
def test_programme_migration_adds_management_fields_and_restricts_delete():
    sql = (
        Path(__file__).resolve().parents[2]
        / "database" / "migrations" / "016_add_programme_management.sql"
    ).read_text()
    assert "total_semesters" in sql
    assert "is_active" in sql
    assert "MAX(sem.semester_number)" in sql
    assert "ON DELETE RESTRICT" in sql


@pytest.mark.unit
def test_cohort_data_respects_programme_semester_limit():
    programme = {"total_semesters": 6}
    data = programme_service.normalize_cohort_data(
        {"semester_number": "6", "section": " c ", "academic_year": "2026-27"}
    )

    assert data == {"semester_number": 6, "section": "C", "academic_year": "2026-27"}
    assert programme_service.validate_cohort_data(data, programme) == {}

    data["semester_number"] = 7
    assert "semester_number" in programme_service.validate_cohort_data(data, programme)


@pytest.mark.unit
def test_used_cohort_cannot_be_permanently_deleted(monkeypatch):
    monkeypatch.setattr(
        programme_service,
        "get_cohort_impact",
        lambda cohort_id: {
            "id": cohort_id, "students": 0, "subjects": 0, "timetable_periods": 1,
            "attendance_sessions": 0, "attendance_records": 0,
        },
    )
    monkeypatch.setattr(programme_service, "_write", lambda *args: pytest.fail("delete must not run"))

    assert programme_service.delete_unused_cohort(9) == "in_use"


@pytest.mark.unit
def test_cohort_migration_archives_and_protects_connected_data():
    sql = (
        Path(__file__).resolve().parents[2]
        / "database" / "migrations" / "017_add_cohort_management.sql"
    ).read_text()
    assert "ADD COLUMN is_active" in sql
    assert "fk_subject_semester" in sql
    assert "fk_timetable_semester" in sql
    assert sql.count("ON DELETE RESTRICT") == 2

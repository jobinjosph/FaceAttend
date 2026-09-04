from datetime import date

import pytest

from services import report_service


def rows():
    base = {
        "session_date": date(2026, 8, 25), "period_number": 1,
        "scheduled_start": "10:00", "scheduled_end": "10:50",
        "subject_id": 4, "subject_code": "CC431", "subject_name": "Cloud Computing",
        "faculty_name": "Dr. Faculty", "first_entry": None, "last_exit": None,
        "total_present_seconds": 0, "marking_method": "MANUAL",
    }
    return [
        {**base, "student_id": 1, "register_number": "25MCA01", "student_name": "Low Student", "status": "PRESENT"},
        {**base, "student_id": 1, "register_number": "25MCA01", "student_name": "Low Student", "status": "ABSENT"},
        {**base, "student_id": 2, "register_number": "25MCA02", "student_name": "Good Student", "status": "PRESENT"},
    ]


@pytest.mark.unit
def test_cohort_report_calculates_and_prioritizes_low_attendance():
    report = report_service.build_cohort_report(rows())

    assert report["summary"]["percentage"] == 66.7
    assert report["low_attendance_count"] == 1
    assert report["students"][0]["register_number"] == "25MCA01"
    assert report["students"][0]["percentage"] == 50.0
    assert report["students"][1]["percentage"] == 100.0


@pytest.mark.unit
def test_cohort_filters_validate_student_subject_month_and_date():
    filters, errors = report_service.normalize_cohort_filters(
        {"student_id": "3", "subject_id": "4", "month": "2026-08", "date": "2026-08-25"}
    )
    assert errors == {}
    assert filters == {
        "student_id": 3, "subject_id": 4, "month": "2026-08",
        "date": "2026-08-25", "semester_id": None,
    }

    _, errors = report_service.normalize_cohort_filters(
        {"student_id": "bad", "subject_id": "0", "month": "August", "date": "yesterday"}
    )
    assert set(errors) == {"student_id", "subject_id", "month", "date"}


@pytest.mark.unit
def test_faculty_report_queries_are_scoped_to_linked_faculty(monkeypatch):
    queries = []

    def fetch_one(query, params=()):
        return {"id": 7, "employee_code": "FC007", "full_name": "Dr. Faculty"}

    def fetch_all(query, params=()):
        queries.append((" ".join(query.split()), params))
        return []

    monkeypatch.setattr(report_service, "_fetch_one", fetch_one)
    monkeypatch.setattr(report_service, "_fetch_all", fetch_all)

    report = report_service.get_cohort_report(22, "FACULTY")

    assert report["faculty"]["id"] == 7
    assert "ats.faculty_id=%s" in queries[0][0]
    assert queries[0][1] == (7,)
    assert "a.faculty_id=%s" in queries[1][0]
    assert queries[1][1] == (7,)
    assert "ats.faculty_id=%s" in queries[2][0]
    assert queries[2][1] == (7,)


@pytest.mark.unit
def test_unsupported_role_cannot_load_cohort_report():
    assert report_service.get_cohort_report(9, "STUDENT") is None

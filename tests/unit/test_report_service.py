from datetime import date, datetime

import pytest

from services import pdf_service, report_service


def row(status, subject_id=1, seconds=0):
    return {
        "session_id": 1, "session_date": date(2026, 8, 20), "period_number": 1,
        "scheduled_start": "10:00", "scheduled_end": "10:50",
        "subject_id": subject_id, "subject_code": f"SUB{subject_id}",
        "subject_name": f"Subject {subject_id}", "faculty_name": "Faculty",
        "status": status, "first_entry": datetime(2026, 8, 20, 10, 1),
        "last_exit": datetime(2026, 8, 20, 10, 48),
        "total_present_seconds": seconds, "marking_method": "FACE",
    }


@pytest.mark.unit
def test_report_calculates_overall_and_subject_percentages():
    report = report_service.build_report(
        {"id": 3, "full_name": "Student"},
        [row("PRESENT", 1, 2820), row("LATE", 1, 2400), row("ABSENT", 1), row("ABSENT", 2)],
    )

    assert report["summary"]["total"] == 4
    assert report["summary"]["attended"] == 2
    assert report["summary"]["percentage"] == 50.0
    assert report["low_attendance"] is True
    assert report["subjects"][0]["percentage"] == 66.7
    assert report["subjects"][0]["low_attendance"] is True
    assert report["history"][0]["duration_label"] == "47m 0s"
    assert report["months"][0]["name"] == "August"
    assert report["months"][0]["subjects"][0]["percentage"] == 66.7
    assert report["dates"][0]["label"] == "20 August 2026"


@pytest.mark.unit
def test_report_filters_are_normalized_and_invalid_values_rejected():
    filters, errors = report_service.normalize_student_filters(
        {"subject_id": "7", "month": "2026-08", "date": "2026-08-22", "semester": "2"}
    )
    assert errors == {}
    assert filters == {"subject_id": 7, "month": "2026-08", "date": "2026-08-22", "semester": 2}

    _, errors = report_service.normalize_student_filters(
        {"subject_id": "bad", "month": "2026-13", "date": "not-a-date", "semester": "5"}
    )
    assert set(errors) == {"subject_id", "month", "date", "semester"}


@pytest.mark.unit
def test_month_options_list_all_twelve_months_for_selected_year():
    options = report_service.get_month_options({"month": "2026-08"})

    assert len(options) == 12
    assert options[0] == {"value": "2026-01", "label": "January"}
    assert options[-1] == {"value": "2026-12", "label": "December"}


@pytest.mark.unit
def test_duration_format_supports_minutes_and_hours():
    assert report_service.format_duration(125) == "2m 5s"
    assert report_service.format_duration(3720) == "1h 2m"


@pytest.mark.unit
def test_pdf_export_creates_valid_pdf_document():
    document = pdf_service.create_text_pdf("Attendance", ["Student: Test", "Attendance: 80%"])
    assert document.startswith(b"%PDF-1.4")
    assert b"xref" in document
    assert document.endswith(b"%%EOF\n")

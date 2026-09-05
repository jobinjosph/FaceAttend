from datetime import date

import pytest

from tests.component.test_attendance_report_routes import sample_cohort_report
from tests.component.test_correction_routes import request_item


@pytest.mark.system
def test_new_academic_group_flows_through_all_admin_workflows(client, monkeypatch):
    context = {
        "id": 77,
        "course_id": 17,
        "course_code": "BSCIT",
        "course_name": "Bachelor of Science in Information Technology",
        "academic_year": "2027-28",
        "semester_number": 6,
        "section": "C",
    }
    selected_ids = {}

    monkeypatch.setattr(
        "services.academic_context_service.list_active_contexts", lambda: [context]
    )
    monkeypatch.setattr(
        "services.academic_context_service.get_active_context",
        lambda semester_id: context if semester_id == context["id"] else None,
    )
    monkeypatch.setattr(
        "services.subject_service.list_subjects",
        lambda search, status, semester_id: selected_ids.update(subjects=semester_id) or [],
    )
    monkeypatch.setattr(
        "services.assignment_service.list_assignments",
        lambda semester_id: selected_ids.update(assignments=semester_id) or [],
    )
    monkeypatch.setattr(
        "services.timetable_service.list_periods",
        lambda semester_id: selected_ids.update(timetable=semester_id) or [],
    )
    monkeypatch.setattr(
        "services.session_service.list_sessions",
        lambda selected_date, semester_id: selected_ids.update(sessions=semester_id) or [],
    )
    monkeypatch.setattr(
        "services.report_service.get_cohort_report",
        lambda user_id, role, filters: selected_ids.update(reports=filters["semester_id"])
        or sample_cohort_report(),
    )
    monkeypatch.setattr(
        "services.correction_service.list_review_requests",
        lambda user_id, role, status, semester_id: selected_ids.update(
            corrections=semester_id
        )
        or [request_item()],
    )

    with client.session_transaction() as user_session:
        user_session.update(user_id=1, full_name="Admin", role="ADMIN")

    selector = (
        "programme=BSCIT&academic_year=2027-28&semester=6&section=C"
    )
    pages = (
        f"/admin/subjects?{selector}",
        f"/admin/faculty-subjects?{selector}",
        f"/admin/timetable?{selector}",
        f"/admin/sessions?date={date(2027, 8, 2).isoformat()}&{selector}",
        f"/reports/attendance?{selector}",
        f"/corrections?status=PENDING&{selector}",
    )

    for path in pages:
        response = client.get(path)
        assert response.status_code == 200
        assert b"BSCIT" in response.data
        assert b"2027-28" in response.data
        assert b"Semester 6" in response.data
        assert b"Section C" in response.data
        for field in ("programme", "academic_year", "semester", "section"):
            assert f'name="{field}"'.encode() in response.data

    assert selected_ids == {
        "subjects": 77,
        "assignments": 77,
        "timetable": 77,
        "sessions": 77,
        "reports": 77,
        "corrections": 77,
    }

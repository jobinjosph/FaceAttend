import pytest


@pytest.mark.system
def test_admin_can_add_edit_and_deactivate_subject_in_selected_group(client, monkeypatch):
    subjects = []

    def create(data, semester_id):
        subjects.append({
            "id": 1, **data, "semester_id": semester_id, "is_active": True,
            "semester_number": 3, "course_code": "MCA",
        })
        return 1

    context = {
        "id": 3, "course_id": 1, "course_code": "MCA",
        "course_name": "Master of Computer Applications", "academic_year": "2026-27",
        "semester_number": 3, "section": "A",
    }
    monkeypatch.setattr("services.academic_context_service.list_active_contexts", lambda: [context])
    monkeypatch.setattr("services.academic_context_service.get_active_context", lambda semester_id: context)
    monkeypatch.setattr("services.subject_service.create_subject", create)
    monkeypatch.setattr("services.subject_service.list_subjects", lambda search, status, semester_id: subjects)
    monkeypatch.setattr("services.subject_service.get_subject", lambda subject_id: subjects[0] if subjects else None)
    monkeypatch.setattr("services.subject_service.update_subject", lambda subject_id, data: subjects[0].update(data) or True)
    monkeypatch.setattr("services.subject_service.set_subject_active", lambda subject_id, active: subjects[0].update(is_active=active) or True)

    with client.session_transaction() as user_session:
        user_session.update(user_id=1, full_name="Admin", role="ADMIN")

    added = client.post("/admin/subjects/add", data={
        "subject_code": "ai433", "subject_name": "Artificial Intelligence",
        "activity_type": "THEORY",
    }, follow_redirects=True)
    assert added.status_code == 200
    assert b"AI433" in added.data

    edited = client.post("/admin/subjects/1/edit", data={
        "subject_code": "AI433", "subject_name": "Applied Artificial Intelligence",
        "activity_type": "PRACTICAL",
    }, follow_redirects=True)
    assert b"Applied Artificial Intelligence" in edited.data

    deactivated = client.post("/admin/subjects/1/status", data={"is_active": "0"}, follow_redirects=True)
    assert b"Inactive" in deactivated.data

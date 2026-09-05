import pytest


@pytest.fixture(autouse=True)
def academic_context(monkeypatch):
    context = {"id": 3, "course_code": "MCA", "course_name": "Master of Computer Applications",
               "semester_number": 3, "section": "A", "academic_year": "2026-27"}
    monkeypatch.setattr("services.academic_context_service.list_active_contexts", lambda: [context])
    monkeypatch.setattr("services.academic_context_service.get_active_context",
                        lambda semester_id: context if semester_id == 3 else None)



@pytest.mark.system
def test_admin_can_assign_and_remove_faculty_from_subject(client, monkeypatch):
    assignments = []
    subjects = [{"id": 3, "subject_code": "CC431", "subject_name": "Cloud Computing"}]
    faculty = [{"id": 8, "employee_code": "FC01", "full_name": "Test Faculty", "email": "faculty@example.com"}]

    def create(data):
        assignments.append({"id": 1, **subjects[0], **faculty[0], **data})
        return 1

    monkeypatch.setattr("services.assignment_service.get_assignment_options", lambda semester_id: (subjects, faculty))
    monkeypatch.setattr("services.assignment_service.active_subject_exists", lambda subject_id, semester_id: True)
    monkeypatch.setattr("services.assignment_service.active_faculty_exists", lambda faculty_id: True)
    monkeypatch.setattr("services.assignment_service.create_assignment", create)
    monkeypatch.setattr("services.assignment_service.list_assignments", lambda semester_id: assignments)
    monkeypatch.setattr("services.assignment_service.get_assignment", lambda assignment_id: assignments[0] if assignments else None)
    monkeypatch.setattr("services.assignment_service.delete_assignment", lambda assignment_id: assignments.clear() or True)

    with client.session_transaction() as session:
        session.update(user_id=1, full_name="Admin", role="ADMIN")

    added = client.post("/admin/faculty-subjects/add", data={"subject_id": "3", "faculty_id": "8"}, follow_redirects=True)
    assert added.status_code == 200
    assert b"Cloud Computing" in added.data
    assert b"Test Faculty" in added.data

    removed = client.post("/admin/faculty-subjects/1/remove", follow_redirects=True)
    assert removed.status_code == 200
    assert b"No faculty assignments yet" in removed.data

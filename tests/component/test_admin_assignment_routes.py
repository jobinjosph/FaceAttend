import pytest


def login_as(client, role):
    with client.session_transaction() as session:
        session.update(user_id=1, full_name="Role User", role=role)


@pytest.mark.component
def test_assignment_list_requires_login(client):
    response = client.get("/admin/faculty-subjects")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


@pytest.mark.component
@pytest.mark.parametrize("role", ["FACULTY", "STUDENT"])
def test_non_admin_cannot_manage_assignments(client, role):
    login_as(client, role)
    assert client.get("/admin/faculty-subjects").status_code == 403
    assert client.get("/admin/faculty-subjects/add").status_code == 403


@pytest.mark.component
def test_admin_can_view_empty_assignment_list(client, monkeypatch):
    login_as(client, "ADMIN")
    monkeypatch.setattr("services.assignment_service.list_assignments", lambda: [])
    response = client.get("/admin/faculty-subjects")
    assert response.status_code == 200
    assert b'<a class="apple-shop-button"' in response.data
    assert b"No faculty assignments yet" in response.data


@pytest.mark.component
def test_assignment_form_lists_active_options(client, monkeypatch):
    login_as(client, "ADMIN")
    monkeypatch.setattr("services.assignment_service.get_assignment_options", lambda: (
        [{"id": 1, "subject_code": "CC431", "subject_name": "Cloud Computing"}],
        [{"id": 2, "employee_code": "FC01", "full_name": "Test Faculty"}],
    ))
    response = client.get("/admin/faculty-subjects/add")
    assert response.status_code == 200
    assert b"CC431" in response.data
    assert b"Test Faculty" in response.data


@pytest.mark.component
def test_empty_assignment_form_shows_validation(client, monkeypatch):
    login_as(client, "ADMIN")
    monkeypatch.setattr("services.assignment_service.get_assignment_options", lambda: ([], []))
    response = client.post("/admin/faculty-subjects/add", data={})
    assert response.status_code == 400
    assert b"Select a subject." in response.data
    assert b"Select a faculty member." in response.data


@pytest.mark.component
def test_unknown_assignment_remove_returns_404(client, monkeypatch):
    login_as(client, "ADMIN")
    monkeypatch.setattr("services.assignment_service.get_assignment", lambda assignment_id: None)
    assert client.post("/admin/faculty-subjects/999/remove").status_code == 404


@pytest.mark.component
def test_assignment_list_filters_selected_non_mca_semester(client, monkeypatch):
    login_as(client, "ADMIN")
    contexts = [
        {"id": 3, "course_code": "MCA", "course_name": "Master of Computer Applications", "semester_number": 3, "section": "A", "academic_year": "2026-27"},
        {"id": 22, "course_code": "BCA", "course_name": "Bachelor of Computer Applications", "semester_number": 2, "section": "A", "academic_year": "2026-27"},
    ]
    captured = {}
    monkeypatch.setattr("services.timetable_service.list_timetable_contexts", lambda: contexts)
    monkeypatch.setattr("services.assignment_service.list_assignments", lambda semester_id: captured.update(semester_id=semester_id) or [])

    response = client.get("/admin/faculty-subjects?programme=BCA&semester=2")

    assert response.status_code == 200
    assert captured["semester_id"] == 22
    assert b"BCA \xe2\x80\x94 Bachelor of Computer Applications" in response.data
    assert b'href="/admin/faculty-subjects/add?semester_id=22"' in response.data


@pytest.mark.component
def test_remove_assignment_returns_to_its_semester(client, monkeypatch):
    login_as(client, "ADMIN")
    monkeypatch.setattr(
        "services.assignment_service.get_assignment",
        lambda assignment_id: {"id": assignment_id, "semester_id": 22},
    )
    monkeypatch.setattr("services.assignment_service.delete_assignment", lambda assignment_id: True)

    response = client.post("/admin/faculty-subjects/7/remove")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/faculty-subjects?semester_id=22")


@pytest.mark.component
@pytest.mark.parametrize("path", [
    "/admin/faculty-subjects?semester_id=999",
    "/admin/faculty-subjects/add?semester_id=999",
])
def test_invalid_assignment_semester_context_returns_404(client, monkeypatch, path):
    login_as(client, "ADMIN")
    monkeypatch.setattr("services.timetable_service.list_timetable_contexts", lambda: [])
    monkeypatch.setattr("services.timetable_service.get_timetable_context", lambda semester_id: None)
    monkeypatch.setattr("services.assignment_service.get_assignment_options", lambda semester_id: ([], []))

    assert client.get(path).status_code == 404

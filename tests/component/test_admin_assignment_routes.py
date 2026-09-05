import pytest


@pytest.fixture(autouse=True)
def academic_context(monkeypatch):
    context = {"id": 3, "course_code": "MCA", "course_name": "Master of Computer Applications",
               "semester_number": 3, "section": "A", "academic_year": "2026-27"}
    monkeypatch.setattr("services.academic_context_service.list_active_contexts", lambda: [context])
    monkeypatch.setattr("services.academic_context_service.get_active_context",
                        lambda semester_id: context if semester_id == 3 else None)



def login_as(client, role):
    with client.session_transaction() as session:
        session.update(user_id=1, full_name="Role User", role=role)


@pytest.mark.component
@pytest.mark.parametrize("year,section,expected", [("2026-27", "A", 41), ("2026-27", "C", 42), ("2027-28", "C", 43)])
def test_assignment_selector_separates_years_and_sections(client, monkeypatch, year, section, expected):
    login_as(client, "ADMIN")
    contexts = [dict(id=identifier, course_code="NEW", course_name="New Programme",
                     semester_number=6, academic_year=academic_year, section=group)
                for identifier, academic_year, group in [(41, "2026-27", "A"), (42, "2026-27", "C"), (43, "2027-28", "C")]]
    monkeypatch.setattr("services.academic_context_service.list_active_contexts", lambda: contexts)
    captured = []
    monkeypatch.setattr("services.assignment_service.list_assignments", lambda semester_id: captured.append(semester_id) or [])
    response = client.get(f"/admin/faculty-subjects?programme=NEW&academic_year={year}&semester=6&section={section}")
    assert response.status_code == 200
    assert captured == [expected]
    for field in ["programme", "academic_year", "semester", "section"]:
        assert f'name="{field}"'.encode() in response.data
    assert f'/admin/faculty-subjects/add?semester_id={expected}'.encode() in response.data


@pytest.mark.component
def test_no_groups_does_not_load_or_create_default_assignments(client, monkeypatch):
    login_as(client, "ADMIN")
    monkeypatch.setattr("services.academic_context_service.list_active_contexts", lambda: [])
    def unexpected(*args):
        pytest.fail("No group must not load or create assignments")
    monkeypatch.setattr("services.assignment_service.list_assignments", unexpected)
    monkeypatch.setattr("services.assignment_service.create_assignment", unexpected)
    assert b"No active semester groups" in client.get("/admin/faculty-subjects").data
    response = client.post("/admin/faculty-subjects/add", data={"subject_id": "3", "faculty_id": "8"})
    assert response.status_code == 400
    assert b"No active semester group" in response.data


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
    monkeypatch.setattr("services.assignment_service.list_assignments", lambda semester_id=None: [])
    response = client.get("/admin/faculty-subjects")
    assert response.status_code == 200
    assert b'<a class="apple-shop-button"' in response.data
    assert b"No faculty assignments yet" in response.data


@pytest.mark.component
def test_assignment_form_lists_active_options(client, monkeypatch):
    login_as(client, "ADMIN")
    monkeypatch.setattr("services.assignment_service.get_assignment_options", lambda semester_id: (
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
    monkeypatch.setattr("services.assignment_service.get_assignment_options", lambda semester_id: ([], []))
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
    monkeypatch.setattr("services.academic_context_service.list_active_contexts", lambda: contexts)
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
    monkeypatch.setattr("services.academic_context_service.list_active_contexts", lambda semester_id=None: [])
    monkeypatch.setattr("services.academic_context_service.get_active_context", lambda semester_id: None)
    monkeypatch.setattr("services.assignment_service.get_assignment_options", lambda semester_id: ([], []))

    assert client.get(path).status_code == 404

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

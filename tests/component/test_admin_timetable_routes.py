import pytest


def login_as(client, role):
    with client.session_transaction() as session:
        session.update(user_id=1, full_name="User", role=role)


@pytest.mark.component
def test_timetable_requires_login(client):
    response = client.get("/admin/timetable")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


@pytest.mark.component
@pytest.mark.parametrize("role", ["FACULTY", "STUDENT"])
def test_non_admin_cannot_manage_timetable(client, role):
    login_as(client, role)
    assert client.get("/admin/timetable").status_code == 403
    assert client.get("/admin/timetable/add").status_code == 403


@pytest.mark.component
def test_empty_timetable_displays_six_days(client, monkeypatch):
    login_as(client, "ADMIN")
    monkeypatch.setattr("services.timetable_service.list_periods", lambda: [])
    response = client.get("/admin/timetable")
    assert response.status_code == 200
    for day in (b"Monday", b"Tuesday", b"Wednesday", b"Thursday", b"Friday", b"Saturday"):
        assert day in response.data


@pytest.mark.component
def test_add_form_lists_assigned_subject_and_faculty(client, monkeypatch):
    login_as(client, "ADMIN")
    monkeypatch.setattr("services.timetable_service.get_assignment_options", lambda: [{"id": 1, "subject_code": "CC431", "subject_name": "Cloud Computing", "full_name": "Dr. Bharathi V"}])
    response = client.get("/admin/timetable/add")
    assert response.status_code == 200
    assert b"Cloud Computing" in response.data
    assert b"Dr. Bharathi V" in response.data


@pytest.mark.component
def test_invalid_period_form_shows_errors(client, monkeypatch):
    login_as(client, "ADMIN")
    monkeypatch.setattr("services.timetable_service.get_assignment_options", lambda: [])
    response = client.post("/admin/timetable/add", data={})
    assert response.status_code == 400
    assert b"Select a day from Monday to Saturday" in response.data


@pytest.mark.component
def test_unknown_period_returns_404(client, monkeypatch):
    login_as(client, "ADMIN")
    monkeypatch.setattr("services.timetable_service.get_period", lambda period_id: None)
    assert client.get("/admin/timetable/999/edit").status_code == 404
    assert client.post("/admin/timetable/999/remove").status_code == 404

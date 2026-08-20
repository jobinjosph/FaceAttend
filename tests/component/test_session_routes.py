import pytest


def login(client, role, user_id=1):
    with client.session_transaction() as session: session.update(user_id=user_id, full_name="User", role=role)


@pytest.mark.component
def test_admin_sessions_require_login(client):
    assert client.get("/admin/sessions").status_code == 302


@pytest.mark.component
def test_faculty_sessions_require_faculty_role(client):
    login(client,"ADMIN"); assert client.get("/faculty/sessions").status_code == 403


@pytest.mark.component
def test_admin_can_view_empty_date(client,monkeypatch):
    login(client,"ADMIN"); monkeypatch.setattr("services.session_service.list_sessions",lambda day:[])
    response=client.get("/admin/sessions?date=2026-08-24")
    assert response.status_code==200 and b"No sessions for 2026-08-24" in response.data
    assert b'class="apple-shop-button"' in response.data
    assert b'class="apple-shop-button apple-shop-button-grey"' in response.data
    assert b'class="session-date-field"' in response.data
    assert b'<label for="date">View date</label>' in response.data


@pytest.mark.component
def test_admin_generates_sessions(client,monkeypatch):
    login(client,"ADMIN"); monkeypatch.setattr("services.session_service.generate_sessions",lambda day:6)
    response=client.post("/admin/sessions/generate",data={"session_date":"2026-08-24"},follow_redirects=False)
    assert response.status_code==302 and "date=2026-08-24" in response.headers["Location"]


@pytest.mark.component
def test_faculty_sees_own_sessions(client,monkeypatch):
    login(client,"FACULTY",7); captured={}
    monkeypatch.setattr("services.session_service.list_faculty_sessions",lambda user_id,day:captured.update(user_id=user_id) or [])
    response=client.get("/faculty/sessions?date=2026-08-24")
    assert response.status_code==200 and captured["user_id"]==7


@pytest.mark.component
def test_faculty_cannot_change_unknown_session(client,monkeypatch):
    login(client,"FACULTY"); monkeypatch.setattr("services.session_service.get_faculty_session",lambda *args:None)
    assert client.post("/faculty/sessions/999/end").status_code==404

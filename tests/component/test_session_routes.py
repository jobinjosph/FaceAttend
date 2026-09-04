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
    assert b'class="apple-shop-button apple-shop-button-grey"' in response.data


@pytest.mark.component
def test_faculty_cannot_change_unknown_session(client,monkeypatch):
    login(client,"FACULTY"); monkeypatch.setattr("services.session_service.get_faculty_session",lambda *args:None)
    assert client.post("/faculty/sessions/999/end").status_code==404


@pytest.mark.component
def test_admin_session_list_filters_selected_non_mca_semester(client, monkeypatch):
    login(client, "ADMIN")
    contexts = [
        {"id": 3, "course_code": "MCA", "course_name": "Master of Computer Applications", "semester_number": 3, "section": "A", "academic_year": "2026-27"},
        {"id": 22, "course_code": "BCA", "course_name": "Bachelor of Computer Applications", "semester_number": 2, "section": "A", "academic_year": "2026-27"},
    ]
    captured = {}
    monkeypatch.setattr("services.timetable_service.list_timetable_contexts", lambda: contexts)
    monkeypatch.setattr(
        "services.session_service.list_sessions",
        lambda day, semester_id: captured.update(day=day, semester_id=semester_id) or [],
    )

    response = client.get("/admin/sessions?date=2026-08-24&programme=BCA&semester=2")

    assert response.status_code == 200
    assert captured["semester_id"] == 22
    assert b"BCA \xe2\x80\x94 Bachelor of Computer Applications" in response.data
    assert b'name="semester_id" value="22"' in response.data


@pytest.mark.component
def test_admin_generates_sessions_for_selected_non_mca_semester(client, monkeypatch):
    login(client, "ADMIN")
    context = {
        "id": 22, "course_code": "BCA", "course_name": "Bachelor of Computer Applications",
        "semester_number": 2, "section": "A", "academic_year": "2026-27",
    }
    captured = {}
    monkeypatch.setattr("services.timetable_service.get_timetable_context", lambda semester_id: context)
    monkeypatch.setattr(
        "services.session_service.generate_sessions",
        lambda day, semester_id: captured.update(day=day, semester_id=semester_id) or 2,
    )

    response = client.post(
        "/admin/sessions/generate",
        data={"session_date": "2026-08-24", "semester_id": "22"},
    )

    assert response.status_code == 302
    assert captured["semester_id"] == 22
    assert "date=2026-08-24" in response.headers["Location"]
    assert "semester_id=22" in response.headers["Location"]


@pytest.mark.component
@pytest.mark.parametrize("path,method", [
    ("/admin/sessions?semester_id=999", "get"),
    ("/admin/sessions/generate", "post"),
])
def test_invalid_admin_session_semester_context_returns_404(client, monkeypatch, path, method):
    login(client, "ADMIN")
    monkeypatch.setattr("services.timetable_service.list_timetable_contexts", lambda: [])
    monkeypatch.setattr("services.timetable_service.get_timetable_context", lambda semester_id: None)
    request_method = getattr(client, method)
    response = request_method(
        path,
        data={"session_date": "2026-08-24", "semester_id": "999"} if method == "post" else None,
    )

    assert response.status_code == 404

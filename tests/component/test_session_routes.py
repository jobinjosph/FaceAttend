import pytest


@pytest.fixture(autouse=True)
def academic_context(monkeypatch):
    context = {"id": 3, "course_code": "MCA", "course_name": "Master of Computer Applications",
               "semester_number": 3, "section": "A", "academic_year": "2026-27"}
    monkeypatch.setattr("services.academic_context_service.list_active_contexts", lambda: [context])
    monkeypatch.setattr("services.academic_context_service.get_active_context",
                        lambda semester_id: context if semester_id == 3 else None)


def login(client, role, user_id=1):
    with client.session_transaction() as session: session.update(user_id=user_id, full_name="User", role=role)


@pytest.mark.component
@pytest.mark.parametrize("year,section,expected", [("2026-27", "A", 41), ("2026-27", "C", 42), ("2027-28", "C", 43)])
def test_session_selector_separates_years_and_sections(client, monkeypatch, year, section, expected):
    login(client, "ADMIN")
    contexts = [dict(id=identifier, course_code="NEW", course_name="New Programme",
                     semester_number=6, academic_year=academic_year, section=group)
                for identifier, academic_year, group in [(41, "2026-27", "A"), (42, "2026-27", "C"), (43, "2027-28", "C")]]
    monkeypatch.setattr("services.academic_context_service.list_active_contexts", lambda: contexts)
    captured = []
    monkeypatch.setattr("services.session_service.list_sessions", lambda day, semester_id: captured.append(semester_id) or [])

    response = client.get(f"/admin/sessions?date=2026-08-24&programme=NEW&academic_year={year}&semester=6&section={section}")

    assert response.status_code == 200
    assert captured == [expected]
    for field in ["programme", "academic_year", "semester", "section"]:
        assert f'name="{field}"'.encode() in response.data
    assert b'name="date" value="2026-08-24"' in response.data
    assert f'name="semester_id" value="{expected}"'.encode() in response.data


@pytest.mark.component
def test_no_groups_disables_generation_and_does_not_use_default(client, monkeypatch):
    login(client, "ADMIN")
    monkeypatch.setattr("services.academic_context_service.list_active_contexts", lambda: [])
    def unexpected(*args):
        pytest.fail("No group must not list or generate sessions")
    monkeypatch.setattr("services.session_service.list_sessions", unexpected)
    monkeypatch.setattr("services.session_service.generate_sessions", unexpected)

    response = client.get("/admin/sessions?date=2026-08-24")
    assert response.status_code == 200
    assert b"No active semester groups" in response.data
    assert b"Generate sessions for this date</button>" in response.data
    assert response.data.count(b"disabled") >= 2

    generated = client.post("/admin/sessions/generate", data={"session_date": "2026-08-24"}, follow_redirects=True)
    assert generated.status_code == 200
    assert b"No active semester group is configured" in generated.data


@pytest.mark.component
def test_admin_sessions_require_login(client):
    assert client.get("/admin/sessions").status_code == 302


@pytest.mark.component
def test_faculty_sessions_require_faculty_role(client):
    login(client,"ADMIN"); assert client.get("/faculty/sessions").status_code == 403


@pytest.mark.component
def test_admin_can_view_empty_date(client,monkeypatch):
    login(client,"ADMIN"); monkeypatch.setattr("services.session_service.list_sessions",lambda day, semester_id:[])
    response=client.get("/admin/sessions?date=2026-08-24")
    assert response.status_code==200 and b"No sessions for 2026-08-24" in response.data
    assert b'class="apple-shop-button"' in response.data
    assert b'data-session-date-filter' in response.data
    assert b'>View</button>' not in response.data
    assert b'Generate sessions for this date</button>' in response.data
    assert b'class="session-date-field"' in response.data
    assert b'<label for="date">View date</label>' in response.data


@pytest.mark.component
def test_admin_generates_sessions(client,monkeypatch):
    login(client,"ADMIN"); monkeypatch.setattr("services.session_service.generate_sessions",lambda day, semester_id:6)
    response=client.post("/admin/sessions/generate",data={"session_date":"2026-08-24"},follow_redirects=False)
    assert response.status_code==302 and "date=2026-08-24" in response.headers["Location"]


@pytest.mark.component
def test_faculty_sees_own_sessions(client,monkeypatch):
    login(client,"FACULTY",7); captured={}
    monkeypatch.setattr("services.session_service.list_faculty_sessions",lambda user_id,day:captured.update(user_id=user_id, day=day.isoformat()) or [])
    response=client.get("/faculty/sessions?date=2026-08-24")
    assert response.status_code==200 and captured["user_id"]==7
    assert captured["day"] == "2026-08-24"
    assert b'data-session-date-filter required' in response.data
    assert b'value="2026-08-24"' in response.data
    assert b'>View</button>' not in response.data


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
    monkeypatch.setattr("services.academic_context_service.list_active_contexts", lambda: contexts)
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
    monkeypatch.setattr("services.academic_context_service.get_active_context", lambda semester_id: context)
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
    monkeypatch.setattr("services.academic_context_service.list_active_contexts", lambda: [])
    monkeypatch.setattr("services.academic_context_service.get_active_context", lambda semester_id: None)
    request_method = getattr(client, method)
    response = request_method(
        path,
        data={"session_date": "2026-08-24", "semester_id": "999"} if method == "post" else None,
    )

    assert response.status_code == 404

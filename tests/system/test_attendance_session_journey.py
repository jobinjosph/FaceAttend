import pytest
from datetime import date


@pytest.mark.system
def test_admin_date_filter_preserves_group_without_generating(client, monkeypatch):
    calls = []
    monkeypatch.setattr("services.session_service.list_sessions",
                        lambda day, semester_id: calls.append((day, semester_id)) or [])
    def unexpected_generation(*args):
        pytest.fail("Viewing a date must not generate sessions")
    monkeypatch.setattr("services.session_service.generate_sessions", unexpected_generation)
    with client.session_transaction() as session:
        session.update(user_id=1, full_name="Admin", role="ADMIN")
    response = client.get("/admin/sessions?date=2026-09-29&semester_id=3")
    assert response.status_code == 200
    assert calls == [(date(2026, 9, 29), 3)]
    assert b"data-session-date-filter" in response.data
    assert b">View</button>" not in response.data
    assert b'name="semester_id" value="3"' in response.data
    assert b'name="session_date" value="2026-09-29"' in response.data


@pytest.fixture(autouse=True)
def academic_context(monkeypatch):
    context = {"id": 3, "course_code": "MCA", "course_name": "Master of Computer Applications",
               "semester_number": 3, "section": "A", "academic_year": "2026-27"}
    monkeypatch.setattr("services.academic_context_service.list_active_contexts", lambda: [context])
    monkeypatch.setattr("services.academic_context_service.get_active_context",
                        lambda semester_id: context if semester_id == 3 else None)


@pytest.mark.system
def test_admin_generates_then_faculty_completes_session(client,monkeypatch):
    sessions=[]
    def generate(day, semester_id):
        sessions.append({"id":1,"session_date":day,"period_number":1,"status":"SCHEDULED","scheduled_start":"10:00","scheduled_end":"10:50","subject_code":"MAD432","subject_name":"Mobile Application Development","full_name":"Dr. Gayathri R"}) if not sessions else None
        return 1 if len(sessions)==1 else 0
    monkeypatch.setattr("services.session_service.generate_sessions",generate)
    monkeypatch.setattr("services.session_service.list_sessions",lambda day, semester_id:sessions)
    monkeypatch.setattr("services.session_service.list_faculty_sessions",lambda uid,day:sessions)
    monkeypatch.setattr("services.session_service.get_faculty_session",lambda sid,uid:sessions[0] if sessions else None)
    def start(sid,uid): sessions[0]["status"]="ACTIVE"; return "started"
    def transition(sid,uid,old,new):
        if sessions[0]["status"]!=old:return False
        sessions[0]["status"]=new;return True
    monkeypatch.setattr("services.session_service.start_session",start)
    monkeypatch.setattr("services.session_service.transition_session",transition)
    monkeypatch.setattr("services.session_service.has_unmarked_records",lambda sid:False)
    with client.session_transaction() as session: session.update(user_id=1,full_name="Admin",role="ADMIN")
    generated=client.post("/admin/sessions/generate",data={"session_date":"2026-08-24"},follow_redirects=True)
    assert b"Mobile Application Development" in generated.data
    with client.session_transaction() as session: session.update(user_id=2,full_name="Faculty",role="FACULTY")
    for action,visible in [("start",b"Active"),("end",b"Review"),("confirm",b"Confirmed")]:
        response=client.post(f"/faculty/sessions/1/{action}",follow_redirects=True)
        assert visible in response.data

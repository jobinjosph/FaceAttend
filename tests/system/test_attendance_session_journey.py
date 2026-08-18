import pytest


@pytest.mark.system
def test_admin_generates_then_faculty_completes_session(client,monkeypatch):
    sessions=[]
    def generate(day):
        sessions.append({"id":1,"session_date":day,"period_number":1,"status":"SCHEDULED","scheduled_start":"10:00","scheduled_end":"10:50","subject_code":"MAD432","subject_name":"Mobile Application Development","full_name":"Dr. Gayathri R"}) if not sessions else None
        return 1 if len(sessions)==1 else 0
    monkeypatch.setattr("services.session_service.generate_sessions",generate)
    monkeypatch.setattr("services.session_service.list_sessions",lambda day:sessions)
    monkeypatch.setattr("services.session_service.list_faculty_sessions",lambda uid,day:sessions)
    monkeypatch.setattr("services.session_service.get_faculty_session",lambda sid,uid:sessions[0] if sessions else None)
    def start(sid,uid): sessions[0]["status"]="ACTIVE"; return "started"
    def transition(sid,uid,old,new):
        if sessions[0]["status"]!=old:return False
        sessions[0]["status"]=new;return True
    monkeypatch.setattr("services.session_service.start_session",start)
    monkeypatch.setattr("services.session_service.transition_session",transition)
    with client.session_transaction() as session: session.update(user_id=1,full_name="Admin",role="ADMIN")
    generated=client.post("/admin/sessions/generate",data={"session_date":"2026-08-24"},follow_redirects=True)
    assert b"Mobile Application Development" in generated.data
    with client.session_transaction() as session: session.update(user_id=2,full_name="Faculty",role="FACULTY")
    for action,visible in [("start",b"Active"),("end",b"Review"),("confirm",b"Confirmed")]:
        response=client.post(f"/faculty/sessions/1/{action}",follow_redirects=True)
        assert visible in response.data

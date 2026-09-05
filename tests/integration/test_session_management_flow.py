from datetime import date
import pytest


@pytest.fixture(autouse=True)
def academic_context(monkeypatch):
    context = {"id": 3, "course_code": "MCA", "course_name": "Master of Computer Applications",
               "semester_number": 3, "section": "A", "academic_year": "2026-27"}
    monkeypatch.setattr("services.academic_context_service.list_active_contexts", lambda: [context])
    monkeypatch.setattr("services.academic_context_service.get_active_context",
                        lambda semester_id: context if semester_id == 3 else None)


def login(client,role,user_id=1):
    with client.session_transaction() as session: session.update(user_id=user_id,full_name="User",role=role)


@pytest.mark.integration
def test_duplicate_generation_reports_no_new_sessions(client,monkeypatch):
    login(client,"ADMIN"); monkeypatch.setattr("services.session_service.generate_sessions",lambda day, semester_id:0); monkeypatch.setattr("services.session_service.list_sessions",lambda day, semester_id:[])
    response=client.post("/admin/sessions/generate",data={"session_date":"2026-08-24"},follow_redirects=True)
    assert b"No new sessions were generated" in response.data


@pytest.mark.integration
@pytest.mark.parametrize("path,expected,new",[("end","ACTIVE","REVIEW"),("confirm","REVIEW","CONFIRMED"),("not-conducted","SCHEDULED","NOT_CONDUCTED")])
def test_faculty_status_transitions(client,monkeypatch,path,expected,new):
    login(client,"FACULTY",4); captured={}
    monkeypatch.setattr("services.session_service.get_faculty_session",lambda *args:{"id":2})
    monkeypatch.setattr("services.session_service.has_unmarked_records",lambda *args:False)
    monkeypatch.setattr("services.session_service.transition_session",lambda sid,uid,old,status:captured.update(old=old,new=status,user=uid) or True)
    response=client.post(f"/faculty/sessions/2/{path}")
    assert response.status_code==302 and captured=={"old":expected,"new":new,"user":4}


@pytest.mark.integration
def test_faculty_cannot_start_when_another_session_is_active(client,monkeypatch):
    login(client,"FACULTY"); monkeypatch.setattr("services.session_service.start_session",lambda *args:"already_active")
    monkeypatch.setattr("services.session_service.list_faculty_sessions",lambda *args:[])
    response=client.post("/faculty/sessions/2/start",follow_redirects=True)
    assert b"Finish your active session" in response.data

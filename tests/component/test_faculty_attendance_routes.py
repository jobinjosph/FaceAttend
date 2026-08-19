import pytest


def login(client,role="FACULTY"):
    with client.session_transaction() as session: session.update(user_id=4,full_name="Faculty",role=role)


@pytest.mark.component
def test_roster_requires_login(client): assert client.get("/faculty/sessions/1/attendance").status_code==302


@pytest.mark.component
def test_student_cannot_view_roster(client): login(client,"STUDENT"); assert client.get("/faculty/sessions/1/attendance").status_code==403


@pytest.mark.component
def test_faculty_cannot_view_another_faculty_session(client,monkeypatch):
    login(client); monkeypatch.setattr("services.attendance_service.get_session_details",lambda *args:None)
    assert client.get("/faculty/sessions/8/attendance").status_code==404


@pytest.mark.component
def test_roster_displays_students_and_totals(client,monkeypatch):
    login(client)
    monkeypatch.setattr("services.attendance_service.get_session_details",lambda *args:{"id":1,"session_date":"2026-08-19","period_number":1,"status":"ACTIVE","scheduled_start":"10:00","scheduled_end":"10:50","subject_name":"Cloud Computing"})
    monkeypatch.setattr("services.attendance_service.list_roster",lambda sid:[{"record_id":1,"student_id":2,"status":"NOT_MARKED","first_entry":None,"notes":None,"register_number":"25MCA01","full_name":"Test Student"}])
    monkeypatch.setattr("services.attendance_service.attendance_totals",lambda sid:{"PRESENT":0,"ABSENT":0,"LATE":0,"LEFT_EARLY":0,"NOT_MARKED":1})
    response=client.get("/faculty/sessions/1/attendance")
    assert response.status_code==200 and b"25MCA01" in response.data and b"Not marked" in response.data
    assert b"Save all attendance" in response.data


@pytest.mark.component
def test_confirm_is_blocked_while_students_unmarked(client,monkeypatch):
    login(client); monkeypatch.setattr("services.session_service.get_faculty_session",lambda *args:{"id":1}); monkeypatch.setattr("services.session_service.has_unmarked_records",lambda sid:True); monkeypatch.setattr("services.session_service.list_faculty_sessions",lambda *args:[])
    response=client.post("/faculty/sessions/1/confirm",follow_redirects=True)
    assert b"Mark every student" in response.data


@pytest.mark.component
def test_bulk_save_requires_owned_session(client,monkeypatch):
    login(client); monkeypatch.setattr("services.attendance_service.get_session_details",lambda *args:None)
    assert client.post("/faculty/sessions/99/attendance/save-all").status_code==404

import pytest


@pytest.mark.system
def test_faculty_marks_complete_roster_then_confirms(client,monkeypatch):
    details={"id":1,"session_date":"2026-08-19","period_number":1,"status":"ACTIVE","scheduled_start":"10:00","scheduled_end":"10:50","subject_name":"Cloud Computing"}
    roster=[{"record_id":1,"student_id":10,"status":"NOT_MARKED","first_entry":None,"notes":None,"register_number":"25MCA01","full_name":"Student One"},{"record_id":2,"student_id":11,"status":"NOT_MARKED","first_entry":None,"notes":None,"register_number":"25MCA02","full_name":"Student Two"}]
    def totals(sid):
        return {status:sum(r["status"]==status for r in roster) for status in ("PRESENT","ABSENT","LATE","LEFT_EARLY","NOT_MARKED")}
    def update(sid,student,uid,data):
        next(r for r in roster if r["student_id"]==student).update(status=data["status"],notes=data["notes"]); return "updated"
    monkeypatch.setattr("services.attendance_service.get_session_details",lambda *args:details)
    monkeypatch.setattr("services.attendance_service.list_roster",lambda sid:roster)
    monkeypatch.setattr("services.attendance_service.attendance_totals",totals)
    monkeypatch.setattr("services.attendance_service.update_record",update)
    monkeypatch.setattr("services.session_service.get_faculty_session",lambda *args:details)
    monkeypatch.setattr("services.session_service.has_unmarked_records",lambda sid:any(r["status"]=="NOT_MARKED" for r in roster))
    monkeypatch.setattr("services.session_service.transition_session",lambda *args:details.update(status="CONFIRMED") or True)
    monkeypatch.setattr("services.session_service.list_faculty_sessions",lambda *args:[])
    with client.session_transaction() as session: session.update(user_id=4,full_name="Faculty",role="FACULTY")
    assert b"Not marked" in client.get("/faculty/sessions/1/attendance").data
    client.post("/faculty/sessions/1/attendance/10",data={"status":"PRESENT","notes":""})
    client.post("/faculty/sessions/1/attendance/11",data={"status":"ABSENT","notes":"Sick"})
    confirmed=client.post("/faculty/sessions/1/confirm",follow_redirects=True)
    assert b"Attendance session confirmed" in confirmed.data and details["status"]=="CONFIRMED"

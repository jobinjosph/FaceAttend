import pytest


@pytest.mark.system
def test_faculty_edits_multiple_students_and_saves_once(client,monkeypatch):
    details={"id":1,"session_date":"2026-08-19","period_number":1,"status":"ACTIVE","scheduled_start":"10:00","scheduled_end":"10:50","subject_name":"Cloud Computing"}
    roster=[{"record_id":1,"student_id":10,"status":"NOT_MARKED","first_entry":None,"notes":None,"register_number":"25MCA01","full_name":"Student One"},{"record_id":2,"student_id":11,"status":"NOT_MARKED","first_entry":None,"notes":None,"register_number":"25MCA02","full_name":"Student Two"}]
    def totals(sid): return {status:sum(row["status"]==status for row in roster) for status in ("PRESENT","ABSENT","LATE","LEFT_EARLY","NOT_MARKED")}
    def bulk(sid,uid,records):
        for row in roster: row.update(records[row["student_id"]])
        return "updated"
    monkeypatch.setattr("services.attendance_service.get_session_details",lambda *args:details)
    monkeypatch.setattr("services.attendance_service.list_roster",lambda sid:roster)
    monkeypatch.setattr("services.attendance_service.attendance_totals",totals)
    monkeypatch.setattr("services.attendance_service.update_records_bulk",bulk)
    with client.session_transaction() as session: session.update(user_id=4,full_name="Faculty",role="FACULTY")
    response=client.post("/faculty/sessions/1/attendance/save-all",data={"status_10":"PRESENT","notes_10":"On time","status_11":"LATE","notes_11":"Bus delay"},follow_redirects=True)
    assert b"Saved attendance for 2 student" in response.data
    assert totals(1)["PRESENT"]==1 and totals(1)["LATE"]==1 and totals(1)["NOT_MARKED"]==0

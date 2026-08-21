import pytest


@pytest.mark.system
def test_faculty_recognizes_student_then_sees_present_roster(client, monkeypatch):
    details = {"id": 1, "session_date": "2026-08-20", "period_number": 1,
               "status": "ACTIVE", "scheduled_start": "10:00", "scheduled_end": "10:50",
               "subject_name": "Cloud Computing"}
    roster = [{"record_id": 1, "student_id": 10, "status": "NOT_MARKED",
               "first_entry": None, "last_exit": None, "total_present_seconds": 0,
               "notes": None, "register_number": "25MCA10",
               "full_name": "Test Student"}]

    monkeypatch.setattr("services.attendance_service.get_session_details", lambda *args: details)
    monkeypatch.setattr("services.attendance_service.list_roster", lambda sid: roster)
    monkeypatch.setattr("services.attendance_service.attendance_totals", lambda sid: {
        status: sum(row["status"] == status for row in roster)
        for status in ("PRESENT", "ABSENT", "LATE", "LEFT_EARLY", "NOT_MARKED")
    })
    monkeypatch.setattr("services.face_service.create_embedding", lambda samples: [1.0, 0.0])

    def recognize(session_id, user_id, embedding, mode):
        student = {"id": 10, "register_number": "25MCA10", "full_name": "Test Student"}
        if mode == "ENTRY":
            roster[0].update(status="PRESENT", first_entry=None)
            return {"result": "entry_recorded", "event_type": "ENTRY", "student": student, "score": 0.96, "status": "PRESENT", "duration_seconds": 0}
        roster[0].update(last_exit=None, total_present_seconds=2700)
        return {"result": "exit_recorded", "event_type": "EXIT", "student": student, "score": 0.96, "status": "PRESENT", "duration_seconds": 2700}

    monkeypatch.setattr("services.attendance_service.recognize_and_mark", recognize)
    with client.session_transaction() as session:
        session.update(user_id=4, full_name="Faculty", role="FACULTY")

    camera = client.get("/faculty/sessions/1/attendance/face")
    assert b"Start attendance camera" in camera.data
    assert b"continues automatically" in camera.data
    marked = client.post(
        "/faculty/sessions/1/attendance/face/recognize",
        data={"sample": "data:image/jpeg;base64,YQ==", "mode": "ENTRY"},
    )
    assert marked.get_json()["student"]["register_number"] == "25MCA10"
    exited = client.post(
        "/faculty/sessions/1/attendance/face/recognize",
        data={"sample": "data:image/jpeg;base64,YQ==", "mode": "EXIT"},
    )
    assert exited.get_json()["result"] == "exit_recorded"
    assert exited.get_json()["duration_seconds"] == 2700
    roster_page = client.get("/faculty/sessions/1/attendance")
    assert b"Present" in roster_page.data and b"25MCA10" in roster_page.data
    assert b"Duration" in roster_page.data

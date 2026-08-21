import pytest


def login(client):
    with client.session_transaction() as session: session.update(user_id=4,full_name="Faculty",role="FACULTY")


@pytest.mark.integration
def test_valid_manual_attendance_is_sent_to_service(client,monkeypatch):
    login(client); captured={}
    monkeypatch.setattr("services.attendance_service.update_record",lambda sid,student,uid,data:captured.update(session=sid,student=student,user=uid,data=data) or "updated")
    response=client.post("/faculty/sessions/7/attendance/12",data={"status":"late","notes":"Bus delay"})
    assert response.status_code==302 and captured["data"]=={"status":"LATE","notes":"Bus delay"}


@pytest.mark.integration
def test_confirmed_attendance_update_is_rejected(client,monkeypatch):
    login(client); monkeypatch.setattr("services.attendance_service.update_record",lambda *args:"locked"); monkeypatch.setattr("services.attendance_service.get_session_details",lambda *args:{"id":7,"status":"CONFIRMED","session_date":"2026-08-19","period_number":1,"scheduled_start":"10:00","scheduled_end":"10:50","subject_name":"Cloud"}); monkeypatch.setattr("services.attendance_service.list_roster",lambda sid:[]); monkeypatch.setattr("services.attendance_service.attendance_totals",lambda sid:{"PRESENT":0,"ABSENT":0,"LATE":0,"LEFT_EARLY":0,"NOT_MARKED":0})
    response=client.post("/faculty/sessions/7/attendance/12",data={"status":"PRESENT","notes":""},follow_redirects=True)
    assert b"attendance is locked" in response.data


@pytest.mark.integration
def test_save_all_sends_complete_roster_in_one_service_call(client,monkeypatch):
    login(client); captured={}
    monkeypatch.setattr("services.attendance_service.get_session_details",lambda *args:{"id":7,"status":"ACTIVE"})
    monkeypatch.setattr("services.attendance_service.list_roster",lambda sid:[{"student_id":10},{"student_id":11}])
    monkeypatch.setattr("services.attendance_service.update_records_bulk",lambda sid,uid,records:captured.update(session=sid,user=uid,records=records) or "updated")
    response=client.post("/faculty/sessions/7/attendance/save-all",data={"status_10":"PRESENT","notes_10":"","status_11":"ABSENT","notes_11":"Sick"})
    assert response.status_code==302
    assert captured["records"]=={10:{"status":"PRESENT","notes":""},11:{"status":"ABSENT","notes":"Sick"}}


@pytest.mark.integration
def test_bulk_save_reports_changed_roster(client,monkeypatch):
    login(client)
    monkeypatch.setattr("services.attendance_service.get_session_details",lambda *args:{"id":7,"status":"ACTIVE","session_date":"2026-08-19","period_number":1,"scheduled_start":"10:00","scheduled_end":"10:50","subject_name":"Cloud"})
    monkeypatch.setattr("services.attendance_service.list_roster",lambda sid:[{"student_id":10,"record_id":1,"status":"NOT_MARKED","first_entry":None,"notes":None,"register_number":"25MCA01","full_name":"Student"}])
    monkeypatch.setattr("services.attendance_service.update_records_bulk",lambda *args:"incomplete")
    monkeypatch.setattr("services.attendance_service.attendance_totals",lambda sid:{"PRESENT":0,"ABSENT":0,"LATE":0,"LEFT_EARLY":0,"NOT_MARKED":1})
    response=client.post("/faculty/sessions/7/attendance/save-all",data={"status_10":"PRESENT","notes_10":""},follow_redirects=True)
    assert b"roster changed" in response.data


@pytest.mark.integration
def test_recognized_face_is_sent_to_atomic_attendance_service(client, monkeypatch):
    login(client); captured = {}
    monkeypatch.setattr("services.face_service.create_embedding", lambda samples: [1.0, 0.0])
    monkeypatch.setattr(
        "services.attendance_service.recognize_and_mark",
        lambda sid, uid, embedding, mode: captured.update(
            session=sid, user=uid, embedding=embedding, mode=mode
        ) or {"result": "entry_recorded", "event_type": "ENTRY", "student": {"id": 2, "full_name": "Student", "register_number": "25MCA02"}, "score": 0.91},
    )
    response = client.post(
        "/faculty/sessions/7/attendance/face/recognize",
        data={"sample": "data:image/jpeg;base64,YQ=="},
    )
    assert response.status_code == 200
    assert response.get_json()["result"] == "entry_recorded"
    assert captured == {"session": 7, "user": 4, "embedding": [1.0, 0.0], "mode": "ENTRY"}


@pytest.mark.integration
def test_exit_mode_is_sent_to_atomic_attendance_service(client, monkeypatch):
    login(client); captured = {}
    monkeypatch.setattr("services.face_service.create_embedding", lambda samples: [1.0, 0.0])
    monkeypatch.setattr(
        "services.attendance_service.recognize_and_mark",
        lambda sid, uid, embedding, mode: captured.update(mode=mode) or {
            "result": "exit_recorded", "event_type": "EXIT",
            "student": {"id": 2, "full_name": "Student", "register_number": "25MCA02"},
            "score": 0.91, "duration_seconds": 2700, "status": "PRESENT",
        },
    )
    response = client.post(
        "/faculty/sessions/7/attendance/face/recognize",
        data={"sample": "data:image/jpeg;base64,YQ==", "mode": "EXIT"},
    )
    assert response.status_code == 200
    assert response.get_json()["duration_seconds"] == 2700
    assert captured == {"mode": "EXIT"}


@pytest.mark.integration
def test_invalid_camera_sample_returns_json_error(client, monkeypatch):
    login(client)
    monkeypatch.setattr(
        "services.face_service.create_embedding",
        lambda samples: (_ for _ in ()).throw(Exception("must not run")),
    )
    response = client.post("/faculty/sessions/7/attendance/face/recognize", data={})
    assert response.status_code == 400
    assert response.get_json()["result"] == "invalid_sample"

import mysql.connector
import pytest


def login(client):
    with client.session_transaction() as session:
        session.update(user_id=1, full_name="Admin", role="ADMIN")


VALID = {"assignment_id": "3", "day_of_week": "1", "period_number": "1", "start_time": "09:00", "end_time": "09:50"}
ASSIGNMENT = {"id": 3, "semester_id": 2, "subject_id": 4, "faculty_id": 5}


@pytest.mark.integration
def test_valid_period_is_created(client, monkeypatch):
    login(client); captured = {}
    monkeypatch.setattr("services.timetable_service.get_assignment", lambda assignment_id: ASSIGNMENT)
    monkeypatch.setattr("services.timetable_service.find_conflict", lambda *args: None)
    monkeypatch.setattr("services.timetable_service.create_period", lambda data, assignment: captured.update(data=data, assignment=assignment) or 1)
    response = client.post("/admin/timetable/add", data=VALID)
    assert response.status_code == 302
    assert captured["data"]["period_number"] == 1


@pytest.mark.integration
@pytest.mark.parametrize("conflict,message", [("semester", b"overlaps another Semester 3 period"), ("faculty", b"teaching another class")])
def test_overlapping_period_is_rejected(client, monkeypatch, conflict, message):
    login(client)
    monkeypatch.setattr("services.timetable_service.get_assignment", lambda assignment_id: ASSIGNMENT)
    monkeypatch.setattr("services.timetable_service.find_conflict", lambda *args: conflict)
    monkeypatch.setattr("services.timetable_service.get_assignment_options", lambda: [])
    response = client.post("/admin/timetable/add", data=VALID)
    assert response.status_code == 400
    assert message in response.data


@pytest.mark.integration
def test_duplicate_day_period_is_rejected(client, monkeypatch):
    login(client)
    monkeypatch.setattr("services.timetable_service.get_assignment", lambda assignment_id: ASSIGNMENT)
    monkeypatch.setattr("services.timetable_service.find_conflict", lambda *args: None)
    monkeypatch.setattr("services.timetable_service.get_assignment_options", lambda: [])
    monkeypatch.setattr("services.timetable_service.create_period", lambda *args: (_ for _ in ()).throw(mysql.connector.IntegrityError("duplicate")))
    response = client.post("/admin/timetable/add", data=VALID)
    assert response.status_code == 409
    assert b"period number is already used" in response.data


@pytest.mark.integration
def test_non_mca_context_is_kept_when_period_validation_fails(client, monkeypatch):
    login(client)
    context = {
        "id": 22,
        "course_code": "BCA",
        "course_name": "Bachelor of Computer Applications",
        "semester_number": 2,
        "section": "A",
        "academic_year": "2026-27",
    }
    monkeypatch.setattr("services.timetable_service.get_period", lambda period_id: {
        "id": period_id, "semester_id": 22, "assignment_id": 3,
    })
    monkeypatch.setattr("services.timetable_service.get_assignment_options", lambda semester_id: [])
    monkeypatch.setattr("services.timetable_service.get_timetable_context", lambda semester_id: context)

    response = client.post("/admin/timetable/8/edit", data={})

    assert response.status_code == 400
    assert b"Admin \xc2\xb7 BCA Semester 2" in response.data
    assert b'name="semester_id" value="22"' in response.data

import pytest


@pytest.mark.system
def test_admin_can_add_edit_view_and_remove_timetable_period(client, monkeypatch):
    periods = []
    assignment = {"id": 3, "semester_id": 2, "subject_id": 4, "faculty_id": 5}
    options = [{"id": 3, "subject_code": "CC431", "subject_name": "Cloud Computing", "full_name": "Dr. Bharathi V"}]

    def create(data, selected):
        periods.append({"id": 1, **data, "subject_code": "CC431", "subject_name": "Cloud Computing", "full_name": "Dr. Bharathi V"})
        return 1
    def update(period_id, data, selected):
        periods[0].update(data); return True

    monkeypatch.setattr("services.timetable_service.get_assignment_options", lambda: options)
    monkeypatch.setattr("services.timetable_service.get_assignment", lambda assignment_id: assignment)
    monkeypatch.setattr("services.timetable_service.find_conflict", lambda *args: None)
    monkeypatch.setattr("services.timetable_service.create_period", create)
    monkeypatch.setattr("services.timetable_service.list_periods", lambda: periods)
    monkeypatch.setattr("services.timetable_service.get_period", lambda period_id: periods[0] if periods else None)
    monkeypatch.setattr("services.timetable_service.update_period", update)
    monkeypatch.setattr("services.timetable_service.delete_period", lambda period_id: periods.clear() or True)
    with client.session_transaction() as session:
        session.update(user_id=1, full_name="Admin", role="ADMIN")

    added = client.post("/admin/timetable/add", data={"assignment_id": "3", "day_of_week": "1", "period_number": "1", "start_time": "09:00", "end_time": "09:50"}, follow_redirects=True)
    assert b"Cloud Computing" in added.data and b"Monday" in added.data
    edited = client.post("/admin/timetable/1/edit", data={"assignment_id": "3", "day_of_week": "2", "period_number": "2", "start_time": "10:00", "end_time": "10:50"}, follow_redirects=True)
    assert b"Tuesday" in edited.data and b"10:00" in edited.data
    removed = client.post("/admin/timetable/1/remove", follow_redirects=True)
    assert b"weekly timetable is empty" in removed.data

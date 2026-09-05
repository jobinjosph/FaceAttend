import pytest


@pytest.fixture(autouse=True)
def academic_context(monkeypatch):
    context = {"id": 3, "course_code": "MCA", "course_name": "Master of Computer Applications",
               "semester_number": 3, "section": "A", "academic_year": "2026-27"}
    monkeypatch.setattr("services.academic_context_service.list_active_contexts", lambda: [context])
    monkeypatch.setattr("services.academic_context_service.get_active_context",
                        lambda semester_id: context if semester_id == 3 else None)


def login_as(client, role):
    with client.session_transaction() as session:
        session.update(user_id=1, full_name="User", role=role)


@pytest.mark.component
@pytest.mark.parametrize("year,section,expected", [("2026-27", "A", 41), ("2026-27", "C", 42), ("2027-28", "C", 43)])
def test_timetable_selector_separates_years_and_sections(client, monkeypatch, year, section, expected):
    login_as(client, "ADMIN")
    contexts = [dict(id=identifier, course_code="NEW", course_name="New Programme",
                     semester_number=6, academic_year=academic_year, section=group)
                for identifier, academic_year, group in [(41, "2026-27", "A"), (42, "2026-27", "C"), (43, "2027-28", "C")]]
    monkeypatch.setattr("services.academic_context_service.list_active_contexts", lambda: contexts)
    captured = []
    monkeypatch.setattr("services.timetable_service.list_periods", lambda semester_id: captured.append(semester_id) or [])

    response = client.get(f"/admin/timetable?programme=NEW&academic_year={year}&semester=6&section={section}")

    assert response.status_code == 200
    assert captured == [expected]
    for field in ["programme", "academic_year", "semester", "section"]:
        assert f'name="{field}"'.encode() in response.data
    assert f'/admin/timetable/add?semester_id={expected}'.encode() in response.data


@pytest.mark.component
def test_no_groups_does_not_load_or_create_default_timetable(client, monkeypatch):
    login_as(client, "ADMIN")
    monkeypatch.setattr("services.academic_context_service.list_active_contexts", lambda: [])
    def unexpected(*args):
        pytest.fail("No group must not load or create timetable data")
    monkeypatch.setattr("services.timetable_service.list_periods", unexpected)
    monkeypatch.setattr("services.timetable_service.create_period", unexpected)

    assert b"No active semester groups" in client.get("/admin/timetable").data
    response = client.post(
        "/admin/timetable/add",
        data={"activity_name": "Library", "day_of_week": "1", "period_number": "1",
              "start_time": "09:00", "end_time": "09:50"},
    )
    assert response.status_code == 400
    assert b"No active semester group" in response.data


@pytest.mark.component
def test_timetable_requires_login(client):
    response = client.get("/admin/timetable")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


@pytest.mark.component
@pytest.mark.parametrize("role", ["FACULTY", "STUDENT"])
def test_non_admin_cannot_manage_timetable(client, role):
    login_as(client, role)
    assert client.get("/admin/timetable").status_code == 403
    assert client.get("/admin/timetable/add").status_code == 403


@pytest.mark.component
def test_empty_timetable_displays_six_days(client, monkeypatch):
    login_as(client, "ADMIN")
    monkeypatch.setattr("services.timetable_service.list_periods", lambda semester_id: [])
    response = client.get("/admin/timetable")
    assert response.status_code == 200
    for day in (b"Monday", b"Tuesday", b"Wednesday", b"Thursday", b"Friday", b"Saturday"):
        assert day in response.data


@pytest.mark.component
def test_add_form_lists_assigned_subject_and_faculty(client, monkeypatch):
    login_as(client, "ADMIN")
    monkeypatch.setattr("services.timetable_service.get_assignment_options", lambda semester_id: [{"id": 1, "subject_code": "CC431", "subject_name": "Cloud Computing", "full_name": "Dr. Bharathi V"}])
    response = client.get("/admin/timetable/add")
    assert response.status_code == 200
    assert b"Cloud Computing" in response.data
    assert b"Dr. Bharathi V" in response.data


@pytest.mark.component
def test_invalid_period_form_shows_errors(client, monkeypatch):
    login_as(client, "ADMIN")
    monkeypatch.setattr("services.timetable_service.get_assignment_options", lambda semester_id: [])
    response = client.post("/admin/timetable/add", data={})
    assert response.status_code == 400
    assert b"Select a day from Monday to Saturday" in response.data


@pytest.mark.component
def test_unknown_period_returns_404(client, monkeypatch):
    login_as(client, "ADMIN")
    monkeypatch.setattr("services.timetable_service.get_period", lambda period_id: None)
    assert client.get("/admin/timetable/999/edit").status_code == 404
    assert client.post("/admin/timetable/999/remove").status_code == 404


@pytest.mark.component
def test_remove_period_returns_to_its_selected_semester(client, monkeypatch):
    login_as(client, "ADMIN")
    monkeypatch.setattr(
        "services.timetable_service.get_period",
        lambda period_id: {"id": period_id, "semester_id": 22},
    )
    monkeypatch.setattr("services.timetable_service.delete_period", lambda period_id: True)

    response = client.post("/admin/timetable/7/remove")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/timetable?semester_id=22")


@pytest.mark.component
@pytest.mark.parametrize("method", ["get", "post"])
def test_invalid_timetable_semester_context_returns_404(client, monkeypatch, method):
    login_as(client, "ADMIN")
    monkeypatch.setattr("services.academic_context_service.get_active_context", lambda semester_id: None)
    request_method = getattr(client, method)

    response = request_method(
        "/admin/timetable/add?semester_id=999",
        data={
            "semester_id": "999",
            "activity_name": "Library",
            "day_of_week": "1",
            "period_number": "1",
            "start_time": "09:00",
            "end_time": "09:50",
        } if method == "post" else None,
    )

    assert response.status_code == 404

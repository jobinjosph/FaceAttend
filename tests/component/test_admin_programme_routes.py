import pytest


def login_admin(client):
    with client.session_transaction() as user_session:
        user_session.update(user_id=1, full_name="Admin", role="ADMIN")


def programme(**overrides):
    item = {
        "id": 2, "code": "BCA", "name": "Bachelor of Computer Applications",
        "total_semesters": 6, "is_active": True, "cohort_count": 4,
        "student_count": 30, "highest_configured_semester": 4,
    }
    item.update(overrides)
    return item


@pytest.mark.component
def test_programme_management_requires_admin(client):
    assert client.get("/admin/programmes").status_code == 302
    with client.session_transaction() as user_session:
        user_session.update(user_id=2, full_name="Student", role="STUDENT")
    assert client.get("/admin/programmes").status_code == 403


@pytest.mark.component
def test_admin_can_view_programme_management(client, monkeypatch):
    login_admin(client)
    monkeypatch.setattr("services.programme_service.list_programmes", lambda: [programme()])

    response = client.get("/admin/programmes")

    assert response.status_code == 200
    assert b"Academic Structure" in response.data
    assert b"Bachelor of Computer Applications" in response.data
    assert b"Archive" in response.data
    assert b'data-delayed-delete' not in response.data


@pytest.mark.component
def test_admin_can_add_programme(client, monkeypatch):
    login_admin(client)
    captured = {}
    monkeypatch.setattr(
        "services.programme_service.create_programme",
        lambda data: captured.update(data=data) or 8,
    )

    response = client.post(
        "/admin/programmes/add",
        data={"code": "BCA", "name": "Bachelor of Computer Applications", "total_semesters": "6"},
    )

    assert response.status_code == 302
    assert captured["data"]["total_semesters"] == 6


@pytest.mark.component
def test_cannot_reduce_total_below_existing_semester(client, monkeypatch):
    login_admin(client)
    monkeypatch.setattr("services.programme_service.get_programme", lambda programme_id: programme())
    monkeypatch.setattr(
        "services.programme_service.update_programme",
        lambda *args: pytest.fail("unsafe update must not run"),
    )

    response = client.post(
        "/admin/programmes/2/edit",
        data={"code": "BCA", "name": "Bachelor of Computer Applications", "total_semesters": "3"},
    )

    assert response.status_code == 400
    assert b"Semester 4 already exists" in response.data


@pytest.mark.component
def test_delete_requires_exact_phrase_and_service_still_checks_usage(client, monkeypatch):
    login_admin(client)
    monkeypatch.setattr("services.programme_service.get_programme", lambda programme_id: programme())
    called = []
    monkeypatch.setattr(
        "services.programme_service.delete_unused_programme",
        lambda programme_id: called.append(programme_id) or "in_use",
    )

    rejected = client.post("/admin/programmes/2/delete", data={"confirmation": "yes"})
    protected = client.post("/admin/programmes/2/delete", data={"confirmation": "DELETE BCA"})

    assert rejected.status_code == 302 and called == [2]
    assert protected.status_code == 302


@pytest.mark.component
def test_unused_programme_has_delayed_delete_dialog(client, monkeypatch):
    login_admin(client)
    monkeypatch.setattr(
        "services.programme_service.list_programmes",
        lambda: [programme(cohort_count=0, student_count=0)],
    )

    response = client.get("/admin/programmes")

    assert b'data-delayed-delete' in response.data
    assert b"Delete in 10 seconds" in response.data
    assert b'name="confirmation"' in response.data


@pytest.mark.component
def test_admin_can_view_and_add_sixth_semester_section(client, monkeypatch):
    login_admin(client)
    monkeypatch.setattr("services.programme_service.get_programme", lambda programme_id: programme())
    monkeypatch.setattr(
        "services.programme_service.list_cohorts",
        lambda programme_id: [{
            "id": 9, "semester_number": 6, "section": "C", "academic_year": "2026-27",
            "is_active": True, "student_count": 0, "subject_count": 0,
            "timetable_count": 0, "session_count": 0,
        }],
    )
    response = client.get("/admin/programmes/2/cohorts")
    assert response.status_code == 200
    assert b"Semester 6" in response.data and b"Section C" in response.data

    captured = {}
    monkeypatch.setattr(
        "services.programme_service.create_cohort",
        lambda programme_id, data: captured.update(programme_id=programme_id, data=data) or 10,
    )
    created = client.post(
        "/admin/programmes/2/cohorts/add",
        data={"semester_number": "6", "section": "D", "academic_year": "2026-27"},
    )
    assert created.status_code == 302
    assert captured == {
        "programme_id": 2,
        "data": {"semester_number": 6, "section": "D", "academic_year": "2026-27"},
    }


@pytest.mark.component
def test_cohort_outside_programme_is_not_editable(client, monkeypatch):
    login_admin(client)
    monkeypatch.setattr("services.programme_service.get_programme", lambda programme_id: programme())
    monkeypatch.setattr("services.programme_service.get_cohort", lambda programme_id, cohort_id: None)

    assert client.get("/admin/programmes/2/cohorts/99/edit").status_code == 404


@pytest.mark.component
def test_cohort_delete_requires_exact_phrase_and_usage_check(client, monkeypatch):
    login_admin(client)
    monkeypatch.setattr("services.programme_service.get_programme", lambda programme_id: programme())
    monkeypatch.setattr(
        "services.programme_service.get_cohort",
        lambda programme_id, cohort_id: {
            "id": cohort_id, "semester_number": 6, "section": "C", "academic_year": "2026-27",
        },
    )
    called = []
    monkeypatch.setattr(
        "services.programme_service.delete_unused_cohort",
        lambda cohort_id: called.append(cohort_id) or "in_use",
    )

    client.post("/admin/programmes/2/cohorts/9/delete", data={"confirmation": "DELETE BCA"})
    client.post(
        "/admin/programmes/2/cohorts/9/delete",
        data={"confirmation": "DELETE BCA S6 C 2026-27"},
    )
    assert called == [9]

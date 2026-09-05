import pytest


CONTEXT = {
    "id": 3, "course_id": 1, "course_code": "MCA",
    "course_name": "Master of Computer Applications", "academic_year": "2026-27",
    "semester_number": 3, "section": "A",
}


@pytest.fixture(autouse=True)
def mock_academic_context(monkeypatch):
    monkeypatch.setattr("services.academic_context_service.list_active_contexts", lambda: [CONTEXT])
    monkeypatch.setattr(
        "services.academic_context_service.get_active_context",
        lambda semester_id: CONTEXT if semester_id == 3 else None,
    )


def login_as(client, role):
    with client.session_transaction() as user_session:
        user_session["user_id"] = 1
        user_session["full_name"] = "Role User"
        user_session["role"] = role


@pytest.mark.component
def test_subject_list_requires_login(client):
    response = client.get("/admin/subjects")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


@pytest.mark.component
@pytest.mark.parametrize("role", ["FACULTY", "STUDENT"])
def test_non_admin_cannot_manage_subjects(client, role):
    login_as(client, role)
    assert client.get("/admin/subjects").status_code == 403
    assert client.get("/admin/subjects/add").status_code == 403


@pytest.mark.component
def test_admin_can_list_subjects_in_selected_academic_group(client, monkeypatch):
    login_as(client, "ADMIN")
    monkeypatch.setattr("services.subject_service.list_subjects", lambda search, status, semester_id: [{
        "id": 1, "subject_code": "CC431", "subject_name": "Cloud Computing",
        "activity_type": "LECTURE", "is_active": True, "semester_number": 3,
        "course_code": "MCA", "academic_year": "2026-27", "section": "A",
    }])
    response = client.get("/admin/subjects")
    assert response.status_code == 200
    assert b'<a class="apple-shop-button"' in response.data
    assert b'class="apple-shop-button apple-shop-button-grey subject-filter-submit"' in response.data
    assert b"Cloud Computing" in response.data
    assert b"Manage Subjects" in response.data
    assert b"Manage subjects across programmes, semesters, and sections." in response.data


@pytest.mark.component
def test_invalid_subject_form_displays_errors(client):
    login_as(client, "ADMIN")
    response = client.post("/admin/subjects/add", data={})
    assert response.status_code == 400
    assert b"Subject code is required." in response.data
    assert b"Subject name is required." in response.data


@pytest.mark.component
def test_admin_can_add_subject(client, monkeypatch):
    login_as(client, "ADMIN")
    created = {}
    monkeypatch.setattr("services.subject_service.create_subject", lambda data, semester_id: created.update(data=data, semester_id=semester_id) or 10)
    response = client.post("/admin/subjects/add", data={
        "subject_code": " ai 433 ", "subject_name": " Artificial Intelligence ",
        "activity_type": "THEORY",
    })
    assert response.status_code == 302
    assert created["semester_id"] == 3
    assert created["data"]["subject_code"] == "AI433"


@pytest.mark.component
def test_unknown_subject_edit_returns_404(client, monkeypatch):
    login_as(client, "ADMIN")
    monkeypatch.setattr("services.subject_service.get_subject", lambda subject_id: None)
    assert client.get("/admin/subjects/999/edit").status_code == 404


@pytest.mark.component
def test_admin_can_deactivate_subject(client, monkeypatch):
    login_as(client, "ADMIN")
    monkeypatch.setattr("services.subject_service.get_subject", lambda subject_id: {"id": subject_id})
    changed = {}
    monkeypatch.setattr("services.subject_service.set_subject_active", lambda subject_id, active: changed.update(id=subject_id, active=active))
    response = client.post("/admin/subjects/7/status", data={"is_active": "0"})
    assert response.status_code == 302
    assert changed == {"id": 7, "active": False}


@pytest.mark.component
@pytest.mark.parametrize("method", ["get", "post"])
def test_invalid_subject_semester_context_returns_404(client, monkeypatch, method):
    login_as(client, "ADMIN")
    monkeypatch.setattr("services.academic_context_service.get_active_context", lambda semester_id: None)
    request_method = getattr(client, method)

    response = request_method(
        "/admin/subjects/add?semester_id=999",
        data={
            "semester_id": "999",
            "subject_code": "TEST101",
            "subject_name": "Test Subject",
            "activity_type": "LECTURE",
        } if method == "post" else None,
    )

    assert response.status_code == 404


@pytest.mark.component
def test_manage_subjects_selects_exact_non_mca_academic_group(client, monkeypatch):
    login_as(client, "ADMIN")
    contexts = [
        CONTEXT,
        {
            "id": 22, "course_id": 2, "course_code": "BCA",
            "course_name": "Bachelor of Computer Applications",
            "academic_year": "2027-28", "semester_number": 2, "section": "C",
        },
    ]
    monkeypatch.setattr("services.academic_context_service.list_active_contexts", lambda: contexts)
    captured = {}
    monkeypatch.setattr(
        "services.subject_service.list_subjects",
        lambda search, status, semester_id: captured.update(semester_id=semester_id) or [],
    )

    response = client.get(
        "/admin/subjects?programme=BCA&academic_year=2027-28&semester=2&section=C"
    )

    assert response.status_code == 200
    assert captured["semester_id"] == 22
    assert b"BCA \xe2\x80\x94 Bachelor of Computer Applications" in response.data
    assert b">2027-28</option>" in response.data
    assert b">Semester 2</option>" in response.data
    assert b">Section C</option>" in response.data
    assert b'href="/admin/subjects/add?semester_id=22"' in response.data

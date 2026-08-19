import pytest


def login(client,role):
    with client.session_transaction() as session: session.update(user_id=1,full_name="User",role=role)


@pytest.mark.component
def test_face_registration_requires_login(client): assert client.get("/admin/students/1/face").status_code==302


@pytest.mark.component
@pytest.mark.parametrize("role",["FACULTY","STUDENT"])
def test_only_admin_can_register_faces(client,role):
    login(client,role); assert client.get("/admin/students/1/face").status_code==403


@pytest.mark.component
def test_unknown_student_returns_404(client,monkeypatch):
    login(client,"ADMIN"); monkeypatch.setattr("services.student_service.get_student",lambda sid:None)
    assert client.get("/admin/students/999/face").status_code==404


@pytest.mark.component
def test_admin_can_open_camera_page(client,monkeypatch):
    login(client,"ADMIN"); monkeypatch.setattr("services.student_service.get_student",lambda sid:{"id":sid,"full_name":"Test Student","register_number":"25MCA01"}); monkeypatch.setattr("services.face_service.get_registration",lambda sid:None)
    response=client.get("/admin/students/1/face")
    assert response.status_code==200 and b"Start camera" in response.data and b"Capture sample" in response.data
    assert b"numerical descriptor, not these photos" in response.data


@pytest.mark.component
def test_invalid_samples_show_controlled_error(client,monkeypatch):
    login(client,"ADMIN"); monkeypatch.setattr("services.student_service.get_student",lambda sid:{"id":sid,"full_name":"Test","register_number":"25MCA01"}); monkeypatch.setattr("services.face_service.get_registration",lambda sid:None)
    response=client.post("/admin/students/1/face",data={"samples_json":"[]"})
    assert response.status_code==400 and b"Capture exactly 3" in response.data

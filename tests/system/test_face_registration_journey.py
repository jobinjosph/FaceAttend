import json
import pytest


@pytest.mark.system
def test_admin_registers_replaces_and_removes_student_face(client,monkeypatch):
    registration={}; student={"id":1,"full_name":"Test Student","register_number":"25MCA01"}
    monkeypatch.setattr("services.student_service.get_student",lambda sid:student)
    monkeypatch.setattr("services.face_service.get_registration",lambda sid:registration or None)
    monkeypatch.setattr("services.face_service.create_embedding",lambda samples:[0.5]*128)
    monkeypatch.setattr("services.face_service.save_registration",lambda sid,embedding,count:registration.update(id=1,model_name="opencv-yunet-sface-v1",sample_count=count,updated_at="now"))
    monkeypatch.setattr("services.face_service.remove_registration",lambda sid:registration.clear())
    with client.session_transaction() as session: session.update(user_id=1,full_name="Admin",role="ADMIN")
    samples=json.dumps(["data:image/jpeg;base64,YQ=="]*3)
    registered=client.post("/admin/students/1/face",data={"samples_json":samples},follow_redirects=True)
    assert b"Registered" in registered.data and b"3 samples" in registered.data
    replaced=client.post("/admin/students/1/face",data={"samples_json":samples},follow_redirects=True)
    assert b"Replace face registration" in replaced.data
    removed=client.post("/admin/students/1/face/remove",follow_redirects=True)
    assert b"Start camera" in removed.data and b"Registered" not in removed.data

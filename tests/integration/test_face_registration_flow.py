import json
import pytest


def login(client):
    with client.session_transaction() as session: session.update(user_id=1,full_name="Admin",role="ADMIN")


@pytest.mark.integration
def test_valid_samples_are_processed_and_saved(client,monkeypatch):
    login(client); captured={}
    monkeypatch.setattr("services.student_service.get_student",lambda sid:{"id":sid,"full_name":"Student","register_number":"25MCA01"})
    monkeypatch.setattr("services.face_service.get_registration",lambda sid:None)
    monkeypatch.setattr("services.face_service.create_embedding",lambda samples:[0.1,0.2])
    monkeypatch.setattr("services.face_service.save_registration",lambda sid,embedding,count:captured.update(student=sid,embedding=embedding,count=count))
    response=client.post("/admin/students/1/face",data={"samples_json":json.dumps(["data:image/jpeg;base64,YQ=="]*3)})
    assert response.status_code==302 and captured=={"student":1,"embedding":[0.1,0.2],"count":3}


@pytest.mark.integration
def test_remove_registration_calls_service(client,monkeypatch):
    login(client); removed=[]
    monkeypatch.setattr("services.student_service.get_student",lambda sid:{"id":sid})
    monkeypatch.setattr("services.face_service.remove_registration",lambda sid:removed.append(sid))
    response=client.post("/admin/students/4/face/remove")
    assert response.status_code==302 and removed==[4]

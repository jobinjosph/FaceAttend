import pytest


@pytest.mark.component
def test_homepage_opens(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"FaceAttend" in response.data
    assert b"Smarter attendance." in response.data


@pytest.mark.component
def test_application_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {
        "application": "FaceAttend",
        "status": "ok",
    }

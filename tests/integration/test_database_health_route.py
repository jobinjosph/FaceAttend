import pytest


@pytest.mark.integration
def test_database_health_reports_success_without_real_database(client, monkeypatch):
    monkeypatch.setattr(
        "routes.main.database_health",
        lambda: (True, "Connected to faceattend_test on MySQL test server"),
    )

    response = client.get("/health/database")

    assert response.status_code == 200
    assert response.get_json()["database"] == "ok"


@pytest.mark.integration
def test_database_health_reports_failure_without_real_database(client, monkeypatch):
    monkeypatch.setattr(
        "routes.main.database_health",
        lambda: (False, "Database unavailable"),
    )

    response = client.get("/health/database")

    assert response.status_code == 503
    assert response.get_json() == {
        "database": "error",
        "message": "Database unavailable",
    }

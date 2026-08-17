import pytest


@pytest.mark.system
def test_visitor_can_view_homepage_sections(client):
    response = client.get("/", follow_redirects=True)
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Face Recognition" in page
    assert "Period Tracking" in page
    assert "Entry &amp; Exit" in page or "Entry & Exit" in page
    assert "Attendance Analytics" in page
    assert "Faculty Portal" in page
    assert "Student Portal" in page
    assert "Admin Portal" in page

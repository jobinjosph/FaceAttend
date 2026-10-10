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
    assert "campus-students.jpg" in page
    assert "campus-community.png" in page
    assert 'onclick="return false;' not in page
    assert "Phase 1" not in page
    assert 'href="/login"' in page
    assert "Kristu Jayanti" not in page


@pytest.mark.system
def test_login_uses_shared_campus_theme_and_home_links(client):
    page = client.get('/login').get_data(as_text=True)
    assert 'css/campus.css' in page
    assert 'href="/#features"' in page
    assert 'href="/#workflow"' in page
    assert 'aria-label="Breadcrumb"' in page
    assert 'autocomplete="current-password"' in page
    assert 'Your role is detected automatically' in page


@pytest.mark.system
@pytest.mark.parametrize('asset', ['css/campus.css', 'images/campus-students.jpg', 'images/campus-community.png'])
def test_campus_assets_are_available(client, asset):
    assert client.get('/static/' + asset).status_code == 200

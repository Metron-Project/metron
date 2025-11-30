from django.urls import reverse

HTML_OK_CODE = 200
HTML_REDIRECT = 302


def test_view_url_exists_at_desired_location(db, client):
    resp = client.get("/")
    assert resp.status_code == HTML_OK_CODE


def test_view_url_accessible_by_name(db, client):
    resp = client.get(reverse("home"))
    assert resp.status_code == HTML_OK_CODE


# Statistics View
def test_statistics_view_requires_login(client):
    """Test that statistics view requires authentication."""
    resp = client.get(reverse("statistics"))
    assert resp.status_code == HTML_REDIRECT


def test_statistics_view_accessible_when_logged_in(auto_login_user):
    """Test that statistics view is accessible when logged in."""
    client, _ = auto_login_user()
    resp = client.get(reverse("statistics"))
    assert resp.status_code == HTML_OK_CODE


# def test_view_uses_correct_template(db, client):
#     resp = client.get(reverse("home"))
#     assert resp.status_code == HTML_OK_CODE
#     assertTemplateUsed(resp, "comicsdb/home.html")

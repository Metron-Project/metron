import pytest
from django.apps import apps
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed

HTML_OK_CODE = 200


@pytest.fixture
def first_entry():
    """Return the first entry from the timeline app config."""
    return apps.get_app_config("timeline").entries[0]


# TimelineView


def test_timeline_url_exists(db, client):
    resp = client.get("/timeline/")
    assert resp.status_code == HTML_OK_CODE


def test_timeline_url_accessible_by_name(db, client):
    resp = client.get(reverse("timeline:timeline"))
    assert resp.status_code == HTML_OK_CODE


def test_timeline_uses_correct_template(db, client):
    resp = client.get(reverse("timeline:timeline"))
    assertTemplateUsed(resp, "timeline.html")


def test_timeline_context_has_entries(db, client):
    resp = client.get(reverse("timeline:timeline"))
    assert "entries" in resp.context
    assert len(resp.context["entries"]) > 0


def test_timeline_entries_sorted_reverse_chronological(db, client):
    resp = client.get(reverse("timeline:timeline"))
    keys = [e["key"] for e in resp.context["entries"]]
    assert keys == sorted(keys, reverse=True)


def test_timeline_entry_has_required_fields(db, client):
    resp = client.get(reverse("timeline:timeline"))
    entry = resp.context["entries"][0]
    for field in ("key", "slug", "title", "date", "icon", "icon_color", "content"):
        assert field in entry


# TimelineEntryRevealView


def test_reveal_valid_slug_returns_200(db, client, first_entry):
    resp = client.get(reverse("timeline:reveal", kwargs={"slug": first_entry["slug"]}))
    assert resp.status_code == HTML_OK_CODE


def test_reveal_uses_correct_template(db, client, first_entry):
    resp = client.get(reverse("timeline:reveal", kwargs={"slug": first_entry["slug"]}))
    assertTemplateUsed(resp, "timeline_entry.html")


def test_reveal_invalid_slug_returns_404(db, client):
    resp = client.get(reverse("timeline:reveal", kwargs={"slug": "does-not-exist"}))
    assert resp.status_code == 404


def test_reveal_response_has_bounce_in_classes(db, client, first_entry):
    resp = client.get(reverse("timeline:reveal", kwargs={"slug": first_entry["slug"]}))
    content = resp.content.decode()
    assert "timeline-icon--bounce-in" in content
    assert "timeline-content--bounce-in" in content
    assert "timeline-date--bounce-in" in content


def test_reveal_response_has_no_hidden_classes(db, client, first_entry):
    resp = client.get(reverse("timeline:reveal", kwargs={"slug": first_entry["slug"]}))
    content = resp.content.decode()
    assert "timeline-icon--hidden" not in content
    assert "timeline-content--hidden" not in content


def test_reveal_response_has_no_htmx_attributes(db, client, first_entry):
    resp = client.get(reverse("timeline:reveal", kwargs={"slug": first_entry["slug"]}))
    content = resp.content.decode()
    assert "hx-get" not in content
    assert "hx-trigger" not in content

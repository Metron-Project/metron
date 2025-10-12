from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed

HTML_OK_CODE = 200
HTML_REDIRECT_CODE = 302

PAGINATE_TEST_VAL = 35
PAGINATE_DEFAULT_VAL = 28
PAGINATE_DIFF_VAL = PAGINATE_TEST_VAL - PAGINATE_DEFAULT_VAL


def test_issue_detail(basic_issue, auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(f"/issue/{basic_issue.slug}/")
    assert resp.status_code == HTML_OK_CODE


def test_issue_redirect(basic_issue, auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(f"/issue/{basic_issue.pk}/")
    assert resp.status_code == HTML_REDIRECT_CODE


# Issue Search
def test_issue_search_view_url_exists_at_desired_location(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get("/issue/search")
    assert resp.status_code == HTML_OK_CODE


def test_issue_search_view_url_accessible_by_name(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("issue:search"))
    assert resp.status_code == HTML_OK_CODE


def test_issue_search_view_uses_correct_template(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("issue:search"))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "comicsdb/issue_list.html")


def test_issue_search_pagination_is_thirty(auto_login_user, list_of_issues):
    client, _ = auto_login_user()
    resp = client.get("/issue/search?q=Super")
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["issue_list"]) == PAGINATE_DEFAULT_VAL


def test_issue_search_lists_all_issues(auto_login_user, list_of_issues):
    # Get second page and confirm it has (exactly) remaining 5 items
    client, _ = auto_login_user()
    resp = client.get("/issue/search?page=2&q=Super")
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["issue_list"]) == PAGINATE_DIFF_VAL


# Issue List
def test_issue_list_view_url_exists_at_desired_location(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get("/issue/")
    assert resp.status_code == HTML_OK_CODE


def test_issue_list_view_url_accessible_by_name(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("issue:list"))
    assert resp.status_code == HTML_OK_CODE


def test_issue_list_view_uses_correct_template(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("issue:list"))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "comicsdb/issue_list.html")


def test_issue_list_pagination_is_thirty(auto_login_user, list_of_issues):
    client, _ = auto_login_user()
    resp = client.get(reverse("issue:list"))
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["issue_list"]) == PAGINATE_DEFAULT_VAL


def test_issue_list_lists_second_page(auto_login_user, list_of_issues):
    # Get second page and confirm it has (exactly) remaining 7 items
    client, _ = auto_login_user()
    resp = client.get(reverse("issue:list") + "?page=2")
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["issue_list"]) == PAGINATE_DIFF_VAL


def test_sitemap(auto_login_user):
    client, _ = auto_login_user()
    response = client.get("/sitemap.xml")
    assert response.status_code == HTML_OK_CODE


# Test: Requires login
def test_sync_reprints_requires_login(db, client, tpb_issue):
    """Test that the sync reprints view requires authentication."""
    resp = client.post(reverse("issue:sync-reprints", args=[tpb_issue.slug]))
    assert resp.status_code == HTML_REDIRECT_CODE
    assert "/accounts/login/" in resp.url


# Test: Only works for Trade Paperback series type
def test_sync_reprints_only_trade_paperback(auto_login_user, tpb_issue, single_story_issue):
    """Test that sync works for Trade Paperback series type."""
    client, _ = auto_login_user()
    tpb_issue.reprints.add(single_story_issue)

    resp = client.post(reverse("issue:sync-reprints", args=[tpb_issue.slug]))
    assert resp.status_code == HTML_REDIRECT_CODE

    tpb_issue.refresh_from_db()
    assert tpb_issue.characters.count() == 2  # superman and batman


# Test: Only works for Omnibus series type
def test_sync_reprints_only_omnibus(auto_login_user, omnibus_issue, single_story_issue):
    """Test that sync works for Omnibus series type."""
    client, _ = auto_login_user()
    omnibus_issue.reprints.add(single_story_issue)

    resp = client.post(reverse("issue:sync-reprints", args=[omnibus_issue.slug]))
    assert resp.status_code == HTML_REDIRECT_CODE

    omnibus_issue.refresh_from_db()
    assert omnibus_issue.characters.count() == 2  # superman and batman


# Test: Only works for Hardcover series type
def test_sync_reprints_only_hardcover(auto_login_user, hardcover_issue, single_story_issue):
    """Test that sync works for Hardcover series type."""
    client, _ = auto_login_user()
    hardcover_issue.reprints.add(single_story_issue)

    resp = client.post(reverse("issue:sync-reprints", args=[hardcover_issue.slug]))
    assert resp.status_code == HTML_REDIRECT_CODE

    hardcover_issue.refresh_from_db()
    assert hardcover_issue.characters.count() == 2  # superman and batman


# Test: Rejects non-TPB/Omnibus/Hardcover series types
def test_sync_reprints_rejects_wrong_series_type(auto_login_user, basic_issue, single_story_issue):
    """Test that sync rejects non-TPB/Omnibus/Hardcover series types."""
    client, _ = auto_login_user()
    basic_issue.reprints.add(single_story_issue)

    resp = client.post(reverse("issue:sync-reprints", args=[basic_issue.slug]), follow=True)
    assert resp.status_code == HTML_OK_CODE

    messages = list(resp.context["messages"])
    assert len(messages) == 1
    assert "only works for Trade Paperback, Omnibus and Hardcover" in str(messages[0])

    basic_issue.refresh_from_db()
    assert basic_issue.characters.count() == 0


# Test: Requires reprints to exist
def test_sync_reprints_requires_reprints(auto_login_user, tpb_issue):
    """Test that sync requires the issue to have reprints."""
    client, _ = auto_login_user()

    resp = client.post(reverse("issue:sync-reprints", args=[tpb_issue.slug]), follow=True)
    assert resp.status_code == HTML_OK_CODE

    messages = list(resp.context["messages"])
    assert len(messages) == 1
    assert "No reprinted issues found" in str(messages[0])


# Test: Blocks sync if characters already exist
def test_sync_reprints_blocks_if_characters_exist(
    auto_login_user, tpb_issue, single_story_issue, superman
):
    """Test that sync is blocked if issue already has characters."""
    client, _ = auto_login_user()
    tpb_issue.reprints.add(single_story_issue)
    tpb_issue.characters.add(superman)

    resp = client.post(reverse("issue:sync-reprints", args=[tpb_issue.slug]), follow=True)
    assert resp.status_code == HTML_OK_CODE

    messages = list(resp.context["messages"])
    assert len(messages) == 1
    assert "already has characters or teams assigned" in str(messages[0])

    tpb_issue.refresh_from_db()
    assert tpb_issue.characters.count() == 1  # Only the one we added


# Test: Blocks sync if teams already exist
def test_sync_reprints_blocks_if_teams_exist(
    auto_login_user, tpb_issue, single_story_issue, teen_titans
):
    """Test that sync is blocked if issue already has teams."""
    client, _ = auto_login_user()
    tpb_issue.reprints.add(single_story_issue)
    tpb_issue.teams.add(teen_titans)

    resp = client.post(reverse("issue:sync-reprints", args=[tpb_issue.slug]), follow=True)
    assert resp.status_code == HTML_OK_CODE

    messages = list(resp.context["messages"])
    assert len(messages) == 1
    assert "already has characters or teams assigned" in str(messages[0])

    tpb_issue.refresh_from_db()
    assert tpb_issue.teams.count() == 1  # Only the one we added


# Test: Syncs from single story reprints
def test_sync_reprints_from_single_story(auto_login_user, tpb_issue, single_story_issue):
    """Test that sync works with reprints that have one story title."""
    client, _ = auto_login_user()
    tpb_issue.reprints.add(single_story_issue)

    resp = client.post(reverse("issue:sync-reprints", args=[tpb_issue.slug]), follow=True)
    assert resp.status_code == HTML_OK_CODE

    messages = list(resp.context["messages"])
    assert len(messages) == 1
    assert "Successfully added" in str(messages[0])

    tpb_issue.refresh_from_db()
    assert tpb_issue.characters.count() == 2  # superman and batman
    assert tpb_issue.teams.count() == 0


# Test: Syncs from no story reprints
def test_sync_reprints_from_no_story(auto_login_user, tpb_issue, no_story_issue):
    """Test that sync works with reprints that have no story titles."""
    client, _ = auto_login_user()
    tpb_issue.reprints.add(no_story_issue)

    resp = client.post(reverse("issue:sync-reprints", args=[tpb_issue.slug]), follow=True)
    assert resp.status_code == HTML_OK_CODE

    messages = list(resp.context["messages"])
    assert len(messages) == 1
    assert "Successfully added" in str(messages[0])

    tpb_issue.refresh_from_db()
    assert tpb_issue.characters.count() == 1  # batman
    assert tpb_issue.teams.count() == 1  # avengers


# Test: Skips multi-story reprints
def test_sync_reprints_skips_multi_story(
    auto_login_user, tpb_issue, single_story_issue, multi_story_issue, superman, batman
):
    """Test that sync skips reprints with multiple story titles."""
    client, _ = auto_login_user()
    tpb_issue.reprints.add(single_story_issue, multi_story_issue)

    resp = client.post(reverse("issue:sync-reprints", args=[tpb_issue.slug]), follow=True)
    assert resp.status_code == HTML_OK_CODE

    messages = list(resp.context["messages"])
    # Should have warning about skipped issues AND success message
    assert len(messages) == 2
    assert any("Skipped" in str(msg) for msg in messages)
    assert any("Successfully added" in str(msg) for msg in messages)

    tpb_issue.refresh_from_db()
    # Should only have characters from single_story_issue, not multi_story_issue
    assert tpb_issue.characters.count() == 2  # superman and batman from single_story_issue
    assert superman in tpb_issue.characters.all()
    assert batman in tpb_issue.characters.all()


# Test: Syncs both characters and teams
def test_sync_reprints_syncs_characters_and_teams(
    auto_login_user, tpb_issue, single_story_issue, no_story_issue
):
    """Test that sync adds both characters and teams from reprints."""
    client, _ = auto_login_user()
    tpb_issue.reprints.add(single_story_issue, no_story_issue)

    resp = client.post(reverse("issue:sync-reprints", args=[tpb_issue.slug]), follow=True)
    assert resp.status_code == HTML_OK_CODE

    tpb_issue.refresh_from_db()
    # superman and batman from single_story, batman from no_story (deduplicated)
    assert tpb_issue.characters.count() == 2
    # avengers from no_story
    assert tpb_issue.teams.count() == 1


# Test: Handles no characters/teams in reprints
def test_sync_reprints_no_data_in_reprints(auto_login_user, tpb_issue, basic_issue):
    """Test that sync handles reprints with no characters or teams."""
    client, _ = auto_login_user()
    tpb_issue.reprints.add(basic_issue)

    resp = client.post(reverse("issue:sync-reprints", args=[tpb_issue.slug]), follow=True)
    assert resp.status_code == HTML_OK_CODE

    messages = list(resp.context["messages"])
    assert len(messages) == 1
    assert "No characters or teams found" in str(messages[0])

    tpb_issue.refresh_from_db()
    assert tpb_issue.characters.count() == 0
    assert tpb_issue.teams.count() == 0


# Test: Updates edited_by field
def test_sync_reprints_updates_edited_by(auto_login_user, tpb_issue, single_story_issue):
    """Test that sync updates the edited_by field."""
    client, user = auto_login_user()
    tpb_issue.reprints.add(single_story_issue)

    original_edited_by = tpb_issue.edited_by

    resp = client.post(reverse("issue:sync-reprints", args=[tpb_issue.slug]))
    assert resp.status_code == HTML_REDIRECT_CODE

    tpb_issue.refresh_from_db()
    assert tpb_issue.edited_by == user
    assert tpb_issue.edited_by != original_edited_by


# Test: Redirects to issue detail page
def test_sync_reprints_redirects_to_detail(auto_login_user, tpb_issue, single_story_issue):
    """Test that sync redirects to the issue detail page."""
    client, _ = auto_login_user()
    tpb_issue.reprints.add(single_story_issue)

    resp = client.post(reverse("issue:sync-reprints", args=[tpb_issue.slug]))
    assert resp.status_code == HTML_REDIRECT_CODE
    assert resp.url == reverse("issue:detail", args=[tpb_issue.slug])

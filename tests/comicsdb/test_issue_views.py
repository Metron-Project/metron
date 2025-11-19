from django.urls import reverse
from django.utils import timezone
from pytest_django.asserts import assertTemplateUsed

from comicsdb.models import Credits
from comicsdb.models.creator import Creator
from comicsdb.models.credits import Role
from comicsdb.models.issue import Issue
from comicsdb.models.publisher import Publisher
from comicsdb.models.series import Series, SeriesType

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
    assert "already has characters, teams, or stories assigned" in str(messages[0])

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
    assert "already has characters, teams, or stories assigned" in str(messages[0])

    tpb_issue.refresh_from_db()
    assert tpb_issue.teams.count() == 1  # Only the one we added


# Test: Blocks sync if stories already exist
def test_sync_reprints_blocks_if_stories_exist(auto_login_user, tpb_issue, single_story_issue):
    """Test that sync is blocked if issue already has stories."""
    client, _ = auto_login_user()
    tpb_issue.reprints.add(single_story_issue)
    tpb_issue.name = ["Existing Story"]
    tpb_issue.save()

    resp = client.post(reverse("issue:sync-reprints", args=[tpb_issue.slug]), follow=True)
    assert resp.status_code == HTML_OK_CODE

    messages = list(resp.context["messages"])
    assert len(messages) == 1
    assert "already has characters, teams, or stories assigned" in str(messages[0])

    tpb_issue.refresh_from_db()
    assert len(tpb_issue.name) == 1  # Only the one we added
    assert tpb_issue.name[0] == "Existing Story"


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
    assert len(tpb_issue.name) == 1  # One story title
    assert tpb_issue.name[0] == "The Beginning"


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
    assert len(tpb_issue.name) == 1  # One [Untitled] entry
    assert tpb_issue.name[0] == "[Untitled]"


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
    # Should only have story from single_story_issue
    assert len(tpb_issue.name) == 1
    assert tpb_issue.name[0] == "The Beginning"


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
    # Two stories: "The Beginning" and "[Untitled]"
    assert len(tpb_issue.name) == 2
    assert "The Beginning" in tpb_issue.name
    assert "[Untitled]" in tpb_issue.name


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


# Test: Syncs stories with proper ordering
def test_sync_reprints_maintains_story_order(
    auto_login_user, tpb_issue, create_user, fc_series, superman, batman
):
    """Test that sync maintains the order of stories based on reprint order."""
    client, user = auto_login_user()

    # Create multiple issues with different stories
    issue1 = Issue.objects.create(
        series=fc_series,
        number="10",
        slug="final-crisis-10",
        name=["First Story"],
        cover_date=timezone.now().date(),
        edited_by=user,
        created_by=user,
    )
    issue1.characters.add(superman)

    issue2 = Issue.objects.create(
        series=fc_series,
        number="11",
        slug="final-crisis-11",
        name=["Second Story"],
        cover_date=timezone.now().date(),
        edited_by=user,
        created_by=user,
    )
    issue2.characters.add(batman)

    issue3 = Issue.objects.create(
        series=fc_series,
        number="12",
        slug="final-crisis-12",
        cover_date=timezone.now().date(),
        edited_by=user,
        created_by=user,
    )

    # Add reprints in specific order
    tpb_issue.reprints.add(issue1, issue2, issue3)

    resp = client.post(reverse("issue:sync-reprints", args=[tpb_issue.slug]))
    assert resp.status_code == HTML_REDIRECT_CODE

    tpb_issue.refresh_from_db()
    assert len(tpb_issue.name) == 3
    assert tpb_issue.name[0] == "First Story"
    assert tpb_issue.name[1] == "Second Story"
    assert tpb_issue.name[2] == "[Untitled]"


# Test: Success message includes story count
def test_sync_reprints_success_message_includes_stories(
    auto_login_user, tpb_issue, single_story_issue
):
    """Test that success message includes story title count."""
    client, _ = auto_login_user()
    tpb_issue.reprints.add(single_story_issue)

    resp = client.post(reverse("issue:sync-reprints", args=[tpb_issue.slug]), follow=True)
    assert resp.status_code == HTML_OK_CODE

    messages = list(resp.context["messages"])
    assert len(messages) == 1
    message_text = str(messages[0])
    assert "Successfully added" in message_text
    assert "character(s)" in message_text
    assert "story title(s)" in message_text


# Issue History Views
def test_issue_history_view_requires_login(client, basic_issue):
    """Test that history view requires authentication."""
    resp = client.get(reverse("issue:history", kwargs={"slug": basic_issue.slug}))
    assert resp.status_code == HTML_REDIRECT_CODE


def test_issue_history_view_accessible(auto_login_user, basic_issue):
    """Test that history view is accessible by name."""
    client, _ = auto_login_user()
    resp = client.get(reverse("issue:history", kwargs={"slug": basic_issue.slug}))
    assert resp.status_code == HTML_OK_CODE


def test_issue_history_uses_correct_template(auto_login_user, basic_issue):
    """Test that history view uses the correct template."""
    client, _ = auto_login_user()
    resp = client.get(reverse("issue:history", kwargs={"slug": basic_issue.slug}))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "comicsdb/history_list.html")


def test_issue_history_shows_creation(auto_login_user, basic_issue):
    """Test that history shows the initial creation record."""
    client, _ = auto_login_user()
    resp = client.get(reverse("issue:history", kwargs={"slug": basic_issue.slug}))
    assert resp.status_code == HTML_OK_CODE
    assert "history_list" in resp.context
    assert len(resp.context["history_list"]) >= 1


def test_issue_history_context(auto_login_user, basic_issue):
    """Test that history view context includes object and model name."""
    client, _ = auto_login_user()
    resp = client.get(reverse("issue:history", kwargs={"slug": basic_issue.slug}))
    assert resp.status_code == HTML_OK_CODE
    assert "object" in resp.context
    assert resp.context["object"] == basic_issue
    assert "model_name" in resp.context
    assert resp.context["model_name"] == "issue"


def test_issue_history_m2m_shows_names(auto_login_user, fc_series, fc_arc, superman, teen_titans):
    """Test that M2M field changes show object names instead of IDs."""
    issue = Issue.objects.create(
        series=fc_series,
        number="1",
        slug=f"{fc_series.slug}-1",
        cover_date="2024-01-01",
        created_by=fc_series.created_by,
        edited_by=fc_series.edited_by,
    )

    # Add an arc to trigger M2M history
    issue.arcs.add(fc_arc)

    # Add a character
    issue.characters.add(superman)

    # Add a team
    issue.teams.add(teen_titans)

    client, _ = auto_login_user()
    resp = client.get(reverse("issue:history", kwargs={"slug": issue.slug}))
    assert resp.status_code == HTML_OK_CODE

    # Check that the history list has delta information
    history_list = resp.context["history_list"]
    assert len(history_list) >= 3

    # Find records with delta changes for M2M fields
    found_arc_change = False
    found_character_change = False
    found_team_change = False

    for history_record in history_list:
        if history_record.delta:
            for change in history_record.delta.changes:
                if change.field == "arcs" and change.new:
                    found_arc_change = True
                    assert fc_arc.name in str(change.new)
                elif change.field == "characters" and change.new:
                    found_character_change = True
                    assert "Superman" in str(change.new)
                elif change.field == "teams" and change.new:
                    found_team_change = True
                    assert "Teen Titans" in str(change.new)

    # We should find at least some M2M changes showing names
    assert found_arc_change or found_character_change or found_team_change, (
        "Should have found at least one M2M change with object names"
    )


# Duplicate Credits View Tests
def test_duplicate_credits_requires_login(db, client, basic_issue):
    """Test that duplicate credits view requires authentication."""
    resp = client.post(reverse("issue:duplicate-credits", args=[basic_issue.slug]))
    assert resp.status_code == HTML_REDIRECT_CODE
    assert "/accounts/login/" in resp.url


def test_duplicate_credits_blocks_dc_comics(auto_login_user, basic_issue):
    """Test that duplicate credits is blocked for DC Comics issues."""
    client, _ = auto_login_user()
    resp = client.post(reverse("issue:duplicate-credits", args=[basic_issue.slug]), follow=True)
    assert resp.status_code == HTML_OK_CODE

    messages = list(resp.context["messages"])
    assert len(messages) == 1
    assert "Credit duplication is not allowed for DC Comics" in str(messages[0])


def test_duplicate_credits_blocks_marvel(auto_login_user, omnibus_issue):
    """Test that duplicate credits is blocked for Marvel issues."""
    client, _ = auto_login_user()
    resp = client.post(reverse("issue:duplicate-credits", args=[omnibus_issue.slug]), follow=True)
    assert resp.status_code == HTML_OK_CODE

    messages = list(resp.context["messages"])
    assert len(messages) == 1
    assert "Credit duplication is not allowed for Marvel" in str(messages[0])


def test_duplicate_credits_blocks_if_credits_exist(
    auto_login_user, create_user, john_byrne, writer
):
    """Test that duplicate credits is blocked if issue already has credits."""
    user = create_user()
    client, _ = auto_login_user()

    # Create a non-DC/Marvel publisher
    image_comics = Publisher.objects.create(
        name="Image Comics", slug="image-comics", edited_by=user, created_by=user
    )
    series_type = SeriesType.objects.get(name="Limited Series")
    series = Series.objects.create(
        name="Spawn",
        slug="spawn",
        publisher=image_comics,
        volume="1",
        year_began=1992,
        series_type=series_type,
        edited_by=user,
        created_by=user,
    )

    issue = Issue.objects.create(
        series=series,
        number="1",
        slug="spawn-1",
        cover_date=timezone.now().date(),
        edited_by=user,
        created_by=user,
    )

    # Add a credit
    credit = Credits.objects.create(issue=issue, creator=john_byrne)
    credit.role.add(writer)

    resp = client.post(reverse("issue:duplicate-credits", args=[issue.slug]), follow=True)
    assert resp.status_code == HTML_OK_CODE

    messages = list(resp.context["messages"])
    assert len(messages) == 1
    assert "already has credits assigned" in str(messages[0])


def test_duplicate_credits_requires_previous_issue(auto_login_user, create_user):
    """Test that duplicate credits requires a previous issue to exist."""
    user = create_user()
    client, _ = auto_login_user()

    # Create a non-DC/Marvel publisher
    image_comics = Publisher.objects.create(
        name="Image Comics", slug="image-comics", edited_by=user, created_by=user
    )
    series_type = SeriesType.objects.get(name="Limited Series")
    series = Series.objects.create(
        name="Spawn",
        slug="spawn",
        publisher=image_comics,
        volume="1",
        year_began=1992,
        series_type=series_type,
        edited_by=user,
        created_by=user,
    )

    # Create only one issue (no previous)
    issue = Issue.objects.create(
        series=series,
        number="1",
        slug="spawn-1",
        cover_date=timezone.now().date(),
        edited_by=user,
        created_by=user,
    )

    resp = client.post(reverse("issue:duplicate-credits", args=[issue.slug]), follow=True)
    assert resp.status_code == HTML_OK_CODE

    messages = list(resp.context["messages"])
    assert len(messages) == 1
    assert "No previous issue found" in str(messages[0])


def test_duplicate_credits_requires_previous_issue_has_credits(
    auto_login_user, create_user, john_byrne, writer
):
    """Test that duplicate credits handles case when previous issue has no credits."""
    user = create_user()
    client, _ = auto_login_user()

    # Create a non-DC/Marvel publisher
    image_comics = Publisher.objects.create(
        name="Image Comics", slug="image-comics", edited_by=user, created_by=user
    )
    series_type = SeriesType.objects.get(name="Limited Series")
    series = Series.objects.create(
        name="Spawn",
        slug="spawn",
        publisher=image_comics,
        volume="1",
        year_began=1992,
        series_type=series_type,
        edited_by=user,
        created_by=user,
    )

    # Create two issues
    Issue.objects.create(
        series=series,
        number="1",
        slug="spawn-1",
        cover_date="2024-01-01",
        edited_by=user,
        created_by=user,
    )

    issue2 = Issue.objects.create(
        series=series,
        number="2",
        slug="spawn-2",
        cover_date="2024-02-01",
        edited_by=user,
        created_by=user,
    )

    # Don't add credits to first issue.

    resp = client.post(reverse("issue:duplicate-credits", args=[issue2.slug]), follow=True)
    assert resp.status_code == HTML_OK_CODE

    messages = list(resp.context["messages"])
    assert len(messages) == 1
    assert "No credits found" in str(messages[0])


def test_duplicate_credits_success(auto_login_user, create_user, john_byrne, walter_simonson):
    """Test successful credit duplication from previous issue."""
    user = create_user()
    client, logged_in_user = auto_login_user()

    # Create roles
    writer = Role.objects.create(name="Writer", order=10)
    penciller = Role.objects.create(name="Penciller", order=20)

    # Create a non-DC/Marvel publisher
    image_comics = Publisher.objects.create(
        name="Image Comics", slug="image-comics", edited_by=user, created_by=user
    )
    series_type = SeriesType.objects.get(name="Limited Series")
    series = Series.objects.create(
        name="Spawn",
        slug="spawn",
        publisher=image_comics,
        volume="1",
        year_began=1992,
        series_type=series_type,
        edited_by=user,
        created_by=user,
    )

    # Create two issues
    issue1 = Issue.objects.create(
        series=series,
        number="1",
        slug="spawn-1",
        cover_date="2024-01-01",
        edited_by=user,
        created_by=user,
    )

    issue2 = Issue.objects.create(
        series=series,
        number="2",
        slug="spawn-2",
        cover_date="2024-02-01",
        edited_by=user,
        created_by=user,
    )

    # Add credits to issue1
    credit1 = Credits.objects.create(issue=issue1, creator=john_byrne)
    credit1.role.add(writer, penciller)

    credit2 = Credits.objects.create(issue=issue1, creator=walter_simonson)
    credit2.role.add(penciller)

    # Duplicate credits to issue2
    resp = client.post(reverse("issue:duplicate-credits", args=[issue2.slug]), follow=True)
    assert resp.status_code == HTML_OK_CODE

    messages = list(resp.context["messages"])
    assert len(messages) == 1
    assert "Successfully duplicated 2 credit(s)" in str(messages[0])

    # Verify credits were duplicated
    issue2_credits = Credits.objects.filter(issue=issue2)
    assert issue2_credits.count() == 2

    # Verify creators and roles
    byrne_credit = issue2_credits.get(creator=john_byrne)
    assert byrne_credit.role.count() == 2
    assert writer in byrne_credit.role.all()
    assert penciller in byrne_credit.role.all()

    simonson_credit = issue2_credits.get(creator=walter_simonson)
    assert simonson_credit.role.count() == 1
    assert penciller in simonson_credit.role.all()

    # Verify edited_by was updated
    issue2.refresh_from_db()
    assert issue2.edited_by == logged_in_user


def test_duplicate_credits_skips_cover_only_credits(auto_login_user, create_user, john_byrne):
    """Test that duplicate credits skips variant cover credits (Cover role only)."""
    user = create_user()
    client, _ = auto_login_user()

    # Create roles
    writer = Role.objects.create(name="Writer", order=10)
    cover = Role.objects.create(name="Cover", order=50)

    # Create a non-DC/Marvel publisher
    image_comics = Publisher.objects.create(
        name="Image Comics", slug="image-comics", edited_by=user, created_by=user
    )
    series_type = SeriesType.objects.get(name="Limited Series")
    series = Series.objects.create(
        name="Spawn",
        slug="spawn",
        publisher=image_comics,
        volume="1",
        year_began=1992,
        series_type=series_type,
        edited_by=user,
        created_by=user,
    )

    # Create two issues
    issue1 = Issue.objects.create(
        series=series,
        number="1",
        slug="spawn-1",
        cover_date="2024-01-01",
        edited_by=user,
        created_by=user,
    )

    issue2 = Issue.objects.create(
        series=series,
        number="2",
        slug="spawn-2",
        cover_date="2024-02-01",
        edited_by=user,
        created_by=user,
    )

    # Add regular credit to issue1
    credit1 = Credits.objects.create(issue=issue1, creator=john_byrne)
    credit1.role.add(writer)

    # Add cover-only credit (variant cover) to issue1
    variant_artist = Creator.objects.create(
        name="Variant Artist", slug="variant-artist", edited_by=user, created_by=user
    )
    credit2 = Credits.objects.create(issue=issue1, creator=variant_artist)
    credit2.role.add(cover)

    # Duplicate credits to issue2
    resp = client.post(reverse("issue:duplicate-credits", args=[issue2.slug]), follow=True)
    assert resp.status_code == HTML_OK_CODE

    messages = list(resp.context["messages"])
    assert len(messages) == 1
    assert "Successfully duplicated 1 credit(s)" in str(messages[0])
    assert "Skipped 1 variant cover credit(s)" in str(messages[0])

    # Verify only non-cover credit was duplicated
    issue2_credits = Credits.objects.filter(issue=issue2)
    assert issue2_credits.count() == 1
    assert issue2_credits.first().creator == john_byrne
    assert variant_artist not in [c.creator for c in issue2_credits]


def test_duplicate_credits_allows_cover_with_other_roles(auto_login_user, create_user, john_byrne):
    """Test that duplicate credits allows Cover role when combined with other roles."""
    user = create_user()
    client, _ = auto_login_user()

    # Create roles
    writer = Role.objects.create(name="Writer", order=10)
    cover = Role.objects.create(name="Cover", order=50)

    # Create a non-DC/Marvel publisher
    image_comics = Publisher.objects.create(
        name="Image Comics", slug="image-comics", edited_by=user, created_by=user
    )
    series_type = SeriesType.objects.get(name="Limited Series")
    series = Series.objects.create(
        name="Spawn",
        slug="spawn",
        publisher=image_comics,
        volume="1",
        year_began=1992,
        series_type=series_type,
        edited_by=user,
        created_by=user,
    )

    # Create two issues
    issue1 = Issue.objects.create(
        series=series,
        number="1",
        slug="spawn-1",
        cover_date="2024-01-01",
        edited_by=user,
        created_by=user,
    )

    issue2 = Issue.objects.create(
        series=series,
        number="2",
        slug="spawn-2",
        cover_date="2024-02-01",
        edited_by=user,
        created_by=user,
    )

    # Add credit with both Writer and Cover roles
    credit = Credits.objects.create(issue=issue1, creator=john_byrne)
    credit.role.add(writer, cover)

    # Duplicate credits to issue2
    resp = client.post(reverse("issue:duplicate-credits", args=[issue2.slug]), follow=True)
    assert resp.status_code == HTML_OK_CODE

    messages = list(resp.context["messages"])
    assert len(messages) == 1
    assert "Successfully duplicated 1 credit(s)" in str(messages[0])
    assert "Skipped" not in str(messages[0])

    # Verify credit was duplicated with both roles
    issue2_credits = Credits.objects.filter(issue=issue2)
    assert issue2_credits.count() == 1
    byrne_credit = issue2_credits.first()
    assert byrne_credit.creator == john_byrne
    assert byrne_credit.role.count() == 2
    assert writer in byrne_credit.role.all()
    assert cover in byrne_credit.role.all()


def test_duplicate_credits_redirects_to_detail(auto_login_user, create_user, john_byrne):
    """Test that duplicate credits redirects to the issue detail page."""
    user = create_user()
    client, _ = auto_login_user()

    writer = Role.objects.create(name="Writer", order=10)

    # Create a non-DC/Marvel publisher
    image_comics = Publisher.objects.create(
        name="Image Comics", slug="image-comics", edited_by=user, created_by=user
    )
    series_type = SeriesType.objects.get(name="Limited Series")
    series = Series.objects.create(
        name="Spawn",
        slug="spawn",
        publisher=image_comics,
        volume="1",
        year_began=1992,
        series_type=series_type,
        edited_by=user,
        created_by=user,
    )

    # Create two issues
    issue1 = Issue.objects.create(
        series=series,
        number="1",
        slug="spawn-1",
        cover_date="2024-01-01",
        edited_by=user,
        created_by=user,
    )

    issue2 = Issue.objects.create(
        series=series,
        number="2",
        slug="spawn-2",
        cover_date="2024-02-01",
        edited_by=user,
        created_by=user,
    )

    # Add credit to issue1
    credit = Credits.objects.create(issue=issue1, creator=john_byrne)
    credit.role.add(writer)

    resp = client.post(reverse("issue:duplicate-credits", args=[issue2.slug]))
    assert resp.status_code == HTML_REDIRECT_CODE
    assert resp.url == reverse("issue:detail", args=[issue2.slug])


# Formset Add Row Tests
def test_credits_add_row_requires_login(db, client):
    """Test that credits add-row endpoint requires authentication."""
    resp = client.get(reverse("issue:credits-add-row"))
    assert resp.status_code == HTML_REDIRECT_CODE
    assert "/accounts/login/" in resp.url


def test_credits_add_row_returns_form_html(auto_login_user):
    """Test that credits add-row endpoint returns HTML for a new form."""
    client, _ = auto_login_user()
    resp = client.get(reverse("issue:credits-add-row"), {"form_idx": "2"})
    assert resp.status_code == HTML_OK_CODE
    # Check that the response contains form fields with correct index
    assert b"credits-2" in resp.content
    # Should contain creator field (uses autocomplete widget)
    assert b"credits-2-creator" in resp.content
    # Should contain role field
    assert b"id_credits-2-role" in resp.content


def test_credits_add_row_uses_correct_index(auto_login_user):
    """Test that credits add-row uses the provided form index."""
    client, _ = auto_login_user()

    # Test with index 0
    resp = client.get(reverse("issue:credits-add-row"), {"form_idx": "0"})
    assert resp.status_code == HTML_OK_CODE
    assert b"credits-0" in resp.content
    assert b"credits-0-creator" in resp.content
    assert b"id_credits-0-role" in resp.content

    # Test with index 5
    resp = client.get(reverse("issue:credits-add-row"), {"form_idx": "5"})
    assert resp.status_code == HTML_OK_CODE
    assert b"credits-5" in resp.content
    assert b"credits-5-creator" in resp.content
    assert b"id_credits-5-role" in resp.content


def test_credits_add_row_sequential_indices(auto_login_user):
    """Test that sequential add-row calls use sequential indices."""
    client, _ = auto_login_user()

    # Simulate adding 3 rows in sequence
    for idx in range(3):
        resp = client.get(reverse("issue:credits-add-row"), {"form_idx": str(idx)})
        assert resp.status_code == HTML_OK_CODE
        expected_name = f"credits-{idx}".encode()
        assert expected_name in resp.content


def test_variants_add_row_requires_login(db, client):
    """Test that variants add-row endpoint requires authentication."""
    resp = client.get(reverse("issue:variants-add-row"))
    assert resp.status_code == HTML_REDIRECT_CODE
    assert "/accounts/login/" in resp.url


def test_variants_add_row_returns_form_html(auto_login_user):
    """Test that variants add-row endpoint returns HTML for a new form."""
    client, _ = auto_login_user()
    resp = client.get(reverse("issue:variants-add-row"), {"form_idx": "1"})
    assert resp.status_code == HTML_OK_CODE
    # Check that the response contains form fields
    assert b"variants-1" in resp.content
    # Should contain image field
    assert b"id_variants-1-image" in resp.content


def test_variants_add_row_uses_correct_index(auto_login_user):
    """Test that variants add-row uses the provided form index."""
    client, _ = auto_login_user()

    resp = client.get(reverse("issue:variants-add-row"), {"form_idx": "3"})
    assert resp.status_code == HTML_OK_CODE
    assert b"variants-3" in resp.content
    assert b"id_variants-3-image" in resp.content


def test_attribution_add_row_requires_login(db, client):
    """Test that attribution add-row endpoint requires authentication."""
    resp = client.get(reverse("issue:attribution-add-row"))
    assert resp.status_code == HTML_REDIRECT_CODE
    assert "/accounts/login/" in resp.url


def test_attribution_add_row_returns_form_html(auto_login_user):
    """Test that attribution add-row endpoint returns HTML for a new form."""
    client, _ = auto_login_user()
    resp = client.get(reverse("issue:attribution-add-row"), {"form_idx": "2"})
    assert resp.status_code == HTML_OK_CODE
    # Check that the response contains form fields
    assert b"attribution-2" in resp.content
    # Should contain source field
    assert b"id_attribution-2-source" in resp.content
    # Should contain url field
    assert b"id_attribution-2-url" in resp.content


def test_attribution_add_row_uses_correct_index(auto_login_user):
    """Test that attribution add-row uses the provided form index."""
    client, _ = auto_login_user()

    resp = client.get(reverse("issue:attribution-add-row"), {"form_idx": "4"})
    assert resp.status_code == HTML_OK_CODE
    assert b"attribution-4" in resp.content
    assert b"id_attribution-4-source" in resp.content

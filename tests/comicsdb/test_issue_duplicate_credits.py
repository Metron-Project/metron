"""Tests for copying credits from the previous issue in a series."""

from django.urls import reverse
from django.utils import timezone

from comicsdb.models import Credits
from comicsdb.models.creator import Creator
from comicsdb.models.credits import Role
from comicsdb.models.issue import Issue
from comicsdb.models.publisher import Publisher
from comicsdb.models.series import Series, SeriesType

HTML_OK_CODE = 200
HTML_REDIRECT_CODE = 302


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

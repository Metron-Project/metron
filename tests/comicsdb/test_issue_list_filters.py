"""Tests for filtering the issue list view."""

from datetime import date

from django.urls import reverse
from django.utils import timezone

from comicsdb.models.issue import Issue
from comicsdb.models.publisher import Publisher
from comicsdb.models.series import Series, SeriesType

HTML_OK_CODE = 200


# Issue Filter Tests
def test_issue_filter_quick_search(auto_login_user, create_user, dc_comics, single_issue_type):
    """Test quick search filters by series name with multi-word support."""
    client, user = auto_login_user()

    # Create series with issues
    batman_series = Series.objects.create(
        name="Batman",
        publisher=dc_comics,
        series_type=single_issue_type,
        year_began=2011,
        status=Series.Status.ONGOING,
        volume=1,
        created_by=user,
        edited_by=user,
    )
    superman_series = Series.objects.create(
        name="Superman",
        publisher=dc_comics,
        series_type=single_issue_type,
        year_began=2011,
        status=Series.Status.ONGOING,
        volume=1,
        created_by=user,
        edited_by=user,
    )

    batman_issue = Issue.objects.create(
        series=batman_series,
        number="1",
        cover_date=timezone.now().date(),
        created_by=user,
        edited_by=user,
    )
    superman_issue = Issue.objects.create(
        series=superman_series,
        number="1",
        cover_date=timezone.now().date(),
        created_by=user,
        edited_by=user,
    )

    # Search by series name via quick search
    resp = client.get(reverse("issue:list") + "?q=batman")
    assert resp.status_code == HTML_OK_CODE
    assert batman_issue in resp.context["issue_list"]
    assert superman_issue not in resp.context["issue_list"]


def test_issue_filter_multi_word_search(auto_login_user, create_user, dc_comics, single_issue_type):
    """Test multi-word series name search."""
    client, user = auto_login_user()

    series = Series.objects.create(
        name="Amazing Spider-Man",
        publisher=dc_comics,
        series_type=single_issue_type,
        year_began=1963,
        status=Series.Status.ONGOING,
        volume=1,
        created_by=user,
        edited_by=user,
    )
    issue = Issue.objects.create(
        series=series,
        number="1",
        cover_date=timezone.now().date(),
        created_by=user,
        edited_by=user,
    )

    # Multi-word search should work
    resp = client.get(reverse("issue:list") + "?q=spider+man")
    assert resp.status_code == HTML_OK_CODE
    assert issue in resp.context["issue_list"]


def test_issue_filter_by_series_name(auto_login_user, create_user, dc_comics, single_issue_type):
    """Test advanced series name filter."""
    client, user = auto_login_user()

    batman_series = Series.objects.create(
        name="Batman",
        publisher=dc_comics,
        series_type=single_issue_type,
        year_began=2011,
        status=Series.Status.ONGOING,
        volume=1,
        created_by=user,
        edited_by=user,
    )
    superman_series = Series.objects.create(
        name="Superman",
        publisher=dc_comics,
        series_type=single_issue_type,
        year_began=2011,
        status=Series.Status.ONGOING,
        volume=1,
        created_by=user,
        edited_by=user,
    )

    batman_issue = Issue.objects.create(
        series=batman_series,
        number="1",
        cover_date=timezone.now().date(),
        created_by=user,
        edited_by=user,
    )
    Issue.objects.create(
        series=superman_series,
        number="1",
        cover_date=timezone.now().date(),
        created_by=user,
        edited_by=user,
    )

    # Filter by series_name parameter
    resp = client.get(reverse("issue:list") + "?series_name=batman")
    assert resp.status_code == HTML_OK_CODE
    assert batman_issue in resp.context["issue_list"]
    assert resp.context["issue_list"].count() == 1


def test_issue_filter_by_series_type(auto_login_user, create_user, dc_comics, single_issue_type):
    """Test filter by series type."""
    client, user = auto_login_user()

    # Create TPB series type
    tpb_type = SeriesType.objects.create(name="Trade Paperback")

    batman_series = Series.objects.create(
        name="Batman",
        publisher=dc_comics,
        series_type=single_issue_type,
        year_began=2011,
        status=Series.Status.ONGOING,
        volume=1,
        created_by=user,
        edited_by=user,
    )
    batman_tpb_series = Series.objects.create(
        name="Batman TPB",
        publisher=dc_comics,
        series_type=tpb_type,
        year_began=2011,
        status=Series.Status.ONGOING,
        volume=1,
        created_by=user,
        edited_by=user,
    )

    single_issue = Issue.objects.create(
        series=batman_series,
        number="1",
        cover_date=timezone.now().date(),
        created_by=user,
        edited_by=user,
    )
    Issue.objects.create(
        series=batman_tpb_series,
        number="1",
        cover_date=timezone.now().date(),
        created_by=user,
        edited_by=user,
    )

    # Filter by series type
    resp = client.get(reverse("issue:list") + f"?series_type={single_issue_type.id}")
    assert resp.status_code == HTML_OK_CODE
    assert single_issue in resp.context["issue_list"]
    assert resp.context["issue_list"].count() == 1


def test_issue_filter_by_publisher_name(auto_login_user, create_user, dc_comics, single_issue_type):
    """Test filter by publisher name."""
    client, user = auto_login_user()

    marvel = Publisher.objects.create(name="Marvel", created_by=user, edited_by=user)

    batman_series = Series.objects.create(
        name="Batman",
        publisher=dc_comics,
        series_type=single_issue_type,
        year_began=2011,
        status=Series.Status.ONGOING,
        volume=1,
        created_by=user,
        edited_by=user,
    )
    spiderman_series = Series.objects.create(
        name="Spider-Man",
        publisher=marvel,
        series_type=single_issue_type,
        year_began=1963,
        status=Series.Status.ONGOING,
        volume=1,
        created_by=user,
        edited_by=user,
    )

    batman_issue = Issue.objects.create(
        series=batman_series,
        number="1",
        cover_date=timezone.now().date(),
        created_by=user,
        edited_by=user,
    )
    Issue.objects.create(
        series=spiderman_series,
        number="1",
        cover_date=timezone.now().date(),
        created_by=user,
        edited_by=user,
    )

    # Filter by publisher
    resp = client.get(reverse("issue:list") + "?publisher_name=DC")
    assert resp.status_code == HTML_OK_CODE
    assert batman_issue in resp.context["issue_list"]
    assert resp.context["issue_list"].count() == 1


def test_issue_filter_by_number(auto_login_user, create_user, dc_comics, single_issue_type):
    """Test filter by issue number."""
    client, user = auto_login_user()

    series = Series.objects.create(
        name="Batman",
        publisher=dc_comics,
        series_type=single_issue_type,
        year_began=2011,
        status=Series.Status.ONGOING,
        volume=1,
        created_by=user,
        edited_by=user,
    )

    issue_1 = Issue.objects.create(
        series=series,
        number="1",
        cover_date=timezone.now().date(),
        created_by=user,
        edited_by=user,
    )
    Issue.objects.create(
        series=series,
        number="2",
        cover_date=timezone.now().date(),
        created_by=user,
        edited_by=user,
    )

    # Filter by issue number
    resp = client.get(reverse("issue:list") + "?number=1")
    assert resp.status_code == HTML_OK_CODE
    assert issue_1 in resp.context["issue_list"]
    assert resp.context["issue_list"].count() == 1


def test_issue_filter_by_cover_year(auto_login_user, create_user, dc_comics, single_issue_type):
    """Test filter by cover year."""
    client, user = auto_login_user()

    series = Series.objects.create(
        name="Batman",
        publisher=dc_comics,
        series_type=single_issue_type,
        year_began=2011,
        status=Series.Status.ONGOING,
        volume=1,
        created_by=user,
        edited_by=user,
    )

    issue_2020 = Issue.objects.create(
        series=series,
        number="1",
        cover_date=date(2020, 1, 1),
        created_by=user,
        edited_by=user,
    )
    Issue.objects.create(
        series=series,
        number="2",
        cover_date=date(2021, 1, 1),
        created_by=user,
        edited_by=user,
    )

    # Filter by cover year
    resp = client.get(reverse("issue:list") + "?cover_year=2020")
    assert resp.status_code == HTML_OK_CODE
    assert issue_2020 in resp.context["issue_list"]
    assert resp.context["issue_list"].count() == 1


def test_issue_filter_by_cover_month(auto_login_user, create_user, dc_comics, single_issue_type):
    """Test filter by cover month."""
    client, user = auto_login_user()

    series = Series.objects.create(
        name="Batman",
        publisher=dc_comics,
        series_type=single_issue_type,
        year_began=2011,
        status=Series.Status.ONGOING,
        volume=1,
        created_by=user,
        edited_by=user,
    )

    january_issue = Issue.objects.create(
        series=series,
        number="1",
        cover_date=date(2020, 1, 1),
        created_by=user,
        edited_by=user,
    )
    Issue.objects.create(
        series=series,
        number="2",
        cover_date=date(2020, 6, 1),
        created_by=user,
        edited_by=user,
    )

    # Filter by cover month
    resp = client.get(reverse("issue:list") + "?cover_month=1")
    assert resp.status_code == HTML_OK_CODE
    assert january_issue in resp.context["issue_list"]
    assert resp.context["issue_list"].count() == 1


def test_issue_filter_by_cv_id(auto_login_user, create_user, dc_comics, single_issue_type):
    """Test filter by Comic Vine ID."""
    client, user = auto_login_user()

    series = Series.objects.create(
        name="Batman",
        publisher=dc_comics,
        series_type=single_issue_type,
        year_began=2011,
        status=Series.Status.ONGOING,
        volume=1,
        created_by=user,
        edited_by=user,
    )

    issue_with_cv = Issue.objects.create(
        series=series,
        number="1",
        cover_date=timezone.now().date(),
        cv_id=12345,
        created_by=user,
        edited_by=user,
    )
    Issue.objects.create(
        series=series,
        number="2",
        cover_date=timezone.now().date(),
        created_by=user,
        edited_by=user,
    )

    # Filter by cv_id
    resp = client.get(reverse("issue:list") + "?cv_id=12345")
    assert resp.status_code == HTML_OK_CODE
    assert issue_with_cv in resp.context["issue_list"]
    assert resp.context["issue_list"].count() == 1


def test_issue_filter_by_gcd_id(auto_login_user, create_user, dc_comics, single_issue_type):
    """Test filter by GCD ID."""
    client, user = auto_login_user()

    series = Series.objects.create(
        name="Batman",
        publisher=dc_comics,
        series_type=single_issue_type,
        year_began=2011,
        status=Series.Status.ONGOING,
        volume=1,
        created_by=user,
        edited_by=user,
    )

    issue_with_gcd = Issue.objects.create(
        series=series,
        number="1",
        cover_date=timezone.now().date(),
        gcd_id=67890,
        created_by=user,
        edited_by=user,
    )
    Issue.objects.create(
        series=series,
        number="2",
        cover_date=timezone.now().date(),
        created_by=user,
        edited_by=user,
    )

    # Filter by gcd_id
    resp = client.get(reverse("issue:list") + "?gcd_id=67890")
    assert resp.status_code == HTML_OK_CODE
    assert issue_with_gcd in resp.context["issue_list"]
    assert resp.context["issue_list"].count() == 1


def test_issue_filter_combined(auto_login_user, create_user, dc_comics, single_issue_type):
    """Test multiple filters applied simultaneously."""
    client, user = auto_login_user()

    marvel = Publisher.objects.create(name="Marvel", created_by=user, edited_by=user)

    batman_series = Series.objects.create(
        name="Batman",
        publisher=dc_comics,
        series_type=single_issue_type,
        year_began=2011,
        status=Series.Status.ONGOING,
        volume=1,
        created_by=user,
        edited_by=user,
    )
    spiderman_series = Series.objects.create(
        name="Spider-Man",
        publisher=marvel,
        series_type=single_issue_type,
        year_began=1963,
        status=Series.Status.ONGOING,
        volume=1,
        created_by=user,
        edited_by=user,
    )

    target_issue = Issue.objects.create(
        series=batman_series,
        number="1",
        cover_date=date(2020, 1, 1),
        created_by=user,
        edited_by=user,
    )
    Issue.objects.create(
        series=batman_series,
        number="2",
        cover_date=date(2021, 1, 1),
        created_by=user,
        edited_by=user,
    )
    Issue.objects.create(
        series=spiderman_series,
        number="1",
        cover_date=date(2020, 1, 1),
        created_by=user,
        edited_by=user,
    )

    # Apply multiple filters
    resp = client.get(reverse("issue:list") + "?publisher_name=DC&cover_year=2020&number=1")
    assert resp.status_code == HTML_OK_CODE
    assert target_issue in resp.context["issue_list"]
    assert resp.context["issue_list"].count() == 1


def test_issue_list_context_data(auto_login_user):
    """Test that context includes series_type and has_active_filters."""
    client, _ = auto_login_user()

    resp = client.get(reverse("issue:list"))
    assert resp.status_code == HTML_OK_CODE
    assert "series_type" in resp.context
    assert "has_active_filters" in resp.context
    assert resp.context["has_active_filters"] is False


def test_issue_list_has_active_filters_indicator(
    auto_login_user, create_user, dc_comics, single_issue_type
):
    """Test has_active_filters indicator works correctly."""
    client, user = auto_login_user()

    series = Series.objects.create(
        name="Batman",
        publisher=dc_comics,
        series_type=single_issue_type,
        year_began=2011,
        status=Series.Status.ONGOING,
        volume=1,
        created_by=user,
        edited_by=user,
    )
    Issue.objects.create(
        series=series,
        number="1",
        cover_date=timezone.now().date(),
        created_by=user,
        edited_by=user,
    )

    # With filters active
    resp = client.get(reverse("issue:list") + "?q=batman")
    assert resp.status_code == HTML_OK_CODE
    assert resp.context["has_active_filters"] is True

    # Page parameter should not trigger filter indicator
    resp = client.get(reverse("issue:list") + "?page=1")
    assert resp.status_code == HTML_OK_CODE
    assert resp.context["has_active_filters"] is False


def test_issue_filter_by_store_date_after(
    auto_login_user, create_user, dc_comics, single_issue_type
):
    """Test store_date_after filter returns issues on or after the given date."""
    client, user = auto_login_user()

    series = Series.objects.create(
        name="Batman",
        publisher=dc_comics,
        series_type=single_issue_type,
        year_began=2026,
        status=Series.Status.ONGOING,
        volume=1,
        created_by=user,
        edited_by=user,
    )

    early_issue = Issue.objects.create(
        series=series,
        number="1",
        cover_date=date(2026, 6, 1),
        store_date=date(2026, 6, 1),
        created_by=user,
        edited_by=user,
    )
    later_issue = Issue.objects.create(
        series=series,
        number="2",
        cover_date=date(2026, 7, 1),
        store_date=date(2026, 7, 1),
        created_by=user,
        edited_by=user,
    )

    resp = client.get(reverse("issue:list") + "?store_date_after=2026-07-01")
    assert resp.status_code == HTML_OK_CODE
    assert later_issue in resp.context["issue_list"]
    assert early_issue not in resp.context["issue_list"]
    assert resp.context["issue_list"].count() == 1


def test_issue_filter_by_store_date_before(
    auto_login_user, create_user, dc_comics, single_issue_type
):
    """Test store_date_before filter returns issues on or before the given date."""
    client, user = auto_login_user()

    series = Series.objects.create(
        name="Batman",
        publisher=dc_comics,
        series_type=single_issue_type,
        year_began=2026,
        status=Series.Status.ONGOING,
        volume=1,
        created_by=user,
        edited_by=user,
    )

    early_issue = Issue.objects.create(
        series=series,
        number="1",
        cover_date=date(2026, 6, 1),
        store_date=date(2026, 6, 1),
        created_by=user,
        edited_by=user,
    )
    Issue.objects.create(
        series=series,
        number="2",
        cover_date=date(2026, 8, 1),
        store_date=date(2026, 8, 1),
        created_by=user,
        edited_by=user,
    )

    resp = client.get(reverse("issue:list") + "?store_date_before=2026-07-01")
    assert resp.status_code == HTML_OK_CODE
    assert early_issue in resp.context["issue_list"]
    assert resp.context["issue_list"].count() == 1


def test_issue_filter_by_store_date_range_same_date(
    auto_login_user, create_user, dc_comics, single_issue_type
):
    """Test store_date_after and store_date_before with the same date returns only exact matches."""
    client, user = auto_login_user()

    series = Series.objects.create(
        name="Batman",
        publisher=dc_comics,
        series_type=single_issue_type,
        year_began=2026,
        status=Series.Status.ONGOING,
        volume=1,
        created_by=user,
        edited_by=user,
    )

    target_issue = Issue.objects.create(
        series=series,
        number="1",
        cover_date=date(2026, 7, 1),
        store_date=date(2026, 7, 1),
        created_by=user,
        edited_by=user,
    )
    Issue.objects.create(
        series=series,
        number="2",
        cover_date=date(2026, 6, 1),
        store_date=date(2026, 6, 1),
        created_by=user,
        edited_by=user,
    )
    Issue.objects.create(
        series=series,
        number="3",
        cover_date=date(2026, 8, 1),
        store_date=date(2026, 8, 1),
        created_by=user,
        edited_by=user,
    )

    resp = client.get(
        reverse("issue:list") + "?store_date_after=2026-07-01&store_date_before=2026-07-01"
    )
    assert resp.status_code == HTML_OK_CODE
    assert target_issue in resp.context["issue_list"]
    assert resp.context["issue_list"].count() == 1


def test_issue_filter_by_foc_date_after(auto_login_user, create_user, dc_comics, single_issue_type):
    """Test foc_date_after filter returns issues with FOC date on or after the given date."""
    client, user = auto_login_user()

    series = Series.objects.create(
        name="Batman",
        publisher=dc_comics,
        series_type=single_issue_type,
        year_began=2026,
        status=Series.Status.ONGOING,
        volume=1,
        created_by=user,
        edited_by=user,
    )

    early_issue = Issue.objects.create(
        series=series,
        number="1",
        cover_date=date(2026, 6, 1),
        foc_date=date(2026, 5, 1),
        created_by=user,
        edited_by=user,
    )
    later_issue = Issue.objects.create(
        series=series,
        number="2",
        cover_date=date(2026, 8, 1),
        foc_date=date(2026, 7, 1),
        created_by=user,
        edited_by=user,
    )

    resp = client.get(reverse("issue:list") + "?foc_date_after=2026-07-01")
    assert resp.status_code == HTML_OK_CODE
    assert later_issue in resp.context["issue_list"]
    assert early_issue not in resp.context["issue_list"]
    assert resp.context["issue_list"].count() == 1


def test_issue_filter_by_foc_date_range_same_date(
    auto_login_user, create_user, dc_comics, single_issue_type
):
    """Test foc_date_after and foc_date_before with the same date returns only exact matches."""
    client, user = auto_login_user()

    series = Series.objects.create(
        name="Batman",
        publisher=dc_comics,
        series_type=single_issue_type,
        year_began=2026,
        status=Series.Status.ONGOING,
        volume=1,
        created_by=user,
        edited_by=user,
    )

    target_issue = Issue.objects.create(
        series=series,
        number="1",
        cover_date=date(2026, 7, 1),
        foc_date=date(2026, 7, 1),
        created_by=user,
        edited_by=user,
    )
    Issue.objects.create(
        series=series,
        number="2",
        cover_date=date(2026, 6, 1),
        foc_date=date(2026, 6, 1),
        created_by=user,
        edited_by=user,
    )
    Issue.objects.create(
        series=series,
        number="3",
        cover_date=date(2026, 8, 1),
        foc_date=date(2026, 8, 1),
        created_by=user,
        edited_by=user,
    )

    resp = client.get(
        reverse("issue:list") + "?foc_date_after=2026-07-01&foc_date_before=2026-07-01"
    )
    assert resp.status_code == HTML_OK_CODE
    assert target_issue in resp.context["issue_list"]
    assert resp.context["issue_list"].count() == 1


def test_issue_list_filters_solicitations(auto_login_user, create_user, fc_series):
    user = create_user()
    common = {"series": fc_series, "cover_date": timezone.now().date(), "edited_by": user}
    solicited = Issue.objects.create(
        number="1", desc="Solicitation text", desc_is_solicitation=True, **common
    )
    Issue.objects.create(number="2", **common)
    client, _ = auto_login_user()
    resp = client.get(reverse("issue:list"), {"desc_is_solicitation": "true"})
    assert resp.status_code == HTML_OK_CODE
    assert list(resp.context["issue_list"]) == [solicited]

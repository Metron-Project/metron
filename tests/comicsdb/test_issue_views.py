from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from pytest_django.asserts import assertTemplateUsed

from comicsdb.forms.issue import MINIMUM_YEAR
from comicsdb.models import Rating
from comicsdb.models.issue import Issue
from comicsdb.models.variant import Variant
from issue_ratings.models import IssueRating
from wish_list.models import WishList, WishListItem

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


def test_issue_create_view_minimum_year(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("issue:create"))
    assert resp.status_code == HTML_OK_CODE
    assert resp.context["minimum_year"] == MINIMUM_YEAR
    assert f"minDate: '{MINIMUM_YEAR}-01-01'" in resp.content.decode()


def test_issue_update_view_minimum_year(basic_issue, auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("issue:update", kwargs={"slug": basic_issue.slug}))
    assert resp.status_code == HTML_OK_CODE
    assert resp.context["minimum_year"] == MINIMUM_YEAR
    assert f"minDate: '{MINIMUM_YEAR}-01-01'" in resp.content.decode()


def test_issue_update_view_embeds_stored_solicitation_desc(solicited_issue, auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("issue:update", kwargs={"slug": solicited_issue.slug}))
    assert resp.status_code == HTML_OK_CODE
    assert (
        '<script id="stored-solicitation-desc" type="application/json">"Solicitation text"'
        in resp.content.decode()
    )


def test_issue_update_view_failed_submit_embeds_stored_solicitation_desc(
    solicited_issue, auto_login_user
):
    client, _ = auto_login_user()
    # Missing required fields, so the form re-renders with the posted description.
    resp = client.post(
        reverse("issue:update", kwargs={"slug": solicited_issue.slug}),
        {"desc": "Rewritten by an editor"},
    )
    assert resp.status_code == HTML_OK_CODE
    content = resp.content.decode()
    assert "Rewritten by an editor</textarea>" in content
    assert (
        '<script id="stored-solicitation-desc" type="application/json">"Solicitation text"'
        in content
    )


def test_issue_update_view_omits_stored_desc_when_not_solicitation(basic_issue, auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("issue:update", kwargs={"slug": basic_issue.slug}))
    assert resp.status_code == HTML_OK_CODE
    assert 'id="stored-solicitation-desc"' not in resp.content.decode()


def test_issue_detail_on_wish_list_false_when_not_on_list(basic_issue, auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(f"/issue/{basic_issue.slug}/")
    assert resp.status_code == HTML_OK_CODE
    assert resp.context["on_wish_list"] is False


def test_issue_detail_on_wish_list_true_when_on_list(basic_issue, auto_login_user):
    client, user = auto_login_user()
    wish_list = WishList.objects.create(user=user)
    WishListItem.objects.create(wish_list=wish_list, issue=basic_issue)
    resp = client.get(f"/issue/{basic_issue.slug}/")
    assert resp.status_code == HTML_OK_CODE
    assert resp.context["on_wish_list"] is True


def test_issue_detail_rating_context_no_ratings(basic_issue, auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(f"/issue/{basic_issue.slug}/")
    assert resp.status_code == HTML_OK_CODE
    assert resp.context["average_rating"] is None
    assert resp.context["rating_count"] == 0
    assert resp.context["user_rating"] is None


def test_issue_detail_rating_context_with_ratings(basic_issue, auto_login_user, create_user):
    client, user = auto_login_user()
    other_user = create_user(username="other_rater")
    IssueRating.objects.create(issue=basic_issue, user=user, rating=4)
    IssueRating.objects.create(issue=basic_issue, user=other_user, rating=2)

    resp = client.get(f"/issue/{basic_issue.slug}/")
    assert resp.status_code == HTML_OK_CODE
    assert resp.context["average_rating"] == 3.0
    assert resp.context["rating_count"] == 2
    assert resp.context["user_rating"].rating == 4


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
    resp = client.get("/issue/search?q=final")
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["issue_list"]) == PAGINATE_DEFAULT_VAL


def test_issue_search_lists_all_issues(auto_login_user, list_of_issues):
    # Get second page and confirm it has (exactly) remaining 5 items
    client, _ = auto_login_user()
    resp = client.get("/issue/search?page=2&q=final")
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
    # Should contain role field (uses autocomplete widget)
    assert b'name="credits-2-role"' in resp.content


def test_credits_add_row_uses_correct_index(auto_login_user):
    """Test that credits add-row uses the provided form index."""
    client, _ = auto_login_user()

    # Test with index 0
    resp = client.get(reverse("issue:credits-add-row"), {"form_idx": "0"})
    assert resp.status_code == HTML_OK_CODE
    assert b"credits-0" in resp.content
    assert b"credits-0-creator" in resp.content
    assert b'name="credits-0-role"' in resp.content

    # Test with index 5
    resp = client.get(reverse("issue:credits-add-row"), {"form_idx": "5"})
    assert resp.status_code == HTML_OK_CODE
    assert b"credits-5" in resp.content
    assert b"credits-5-creator" in resp.content
    assert b'name="credits-5-role"' in resp.content


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


@pytest.mark.parametrize(
    ("cover_date", "valid"),
    [("1976-07-01", True), ("2023-01-01", False)],
    ids=["legacy_upc_before_cutoff", "legacy_upc_from_cutoff"],
)
def test_issue_create_checks_variant_upc_against_cover_date(
    settings, tmp_path, auto_login_user, fc_series, cover_date, valid
):
    settings.MEDIA_ROOT = tmp_path
    image = BytesIO()
    Image.new("RGB", (1, 1)).save(image, format="PNG")
    client, _ = auto_login_user()
    data = {
        "series": fc_series.pk,
        "number": "1",
        "cover_date": cover_date,
        "rating": Rating.objects.create(name="Test Rating").pk,
        **{
            f"{prefix}-{field}": "0"
            for prefix in ("credits", "variants", "attribution")
            for field in ("TOTAL_FORMS", "INITIAL_FORMS")
        },
        "variants-TOTAL_FORMS": "1",
        "variants-0-name": "Variant",
        "variants-0-upc": "0714860246207",
        "variants-0-image": SimpleUploadedFile("v.png", image.getvalue(), "image/png"),
    }

    resp = client.post(reverse("issue:create"), data=data)

    if valid:
        issue = Issue.objects.get(series=fc_series, number="1")
        assert issue.variants.filter(upc="0714860246207").exists()
    else:
        # An invalid variant re-renders the form with its error instead of saving the issue.
        assert resp.status_code == HTML_OK_CODE
        assert not Issue.objects.filter(series=fc_series, number="1").exists()
        assert resp.context["variants"].forms[0].errors["upc"] == ["UPC check digit is invalid."]
        assert b'id="section-errors"' in resp.content
        assert b'href="#section-variants"' in resp.content


def test_issue_create_saves_issue_once(auto_login_user, fc_series):
    client, _ = auto_login_user()
    data = {
        "series": fc_series.pk,
        "number": "1",
        "cover_date": "2023-01-01",
        "rating": Rating.objects.create(name="Test Rating").pk,
        **{
            f"{prefix}-{field}": "0"
            for prefix in ("credits", "variants", "attribution")
            for field in ("TOTAL_FORMS", "INITIAL_FORMS")
        },
    }

    resp = client.post(reverse("issue:create"), data=data)

    issue = Issue.objects.get(series=fc_series, number="1")
    assert resp.status_code == HTML_REDIRECT_CODE
    assert resp.url == issue.get_absolute_url()
    # One history row per save.
    assert issue.history.count() == 1


def test_issue_detail_shows_solicitation_tag(solicited_issue, auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("issue:detail", kwargs={"slug": solicited_issue.slug}))
    assert resp.status_code == HTML_OK_CODE
    assert b'<span class="tag is-info ml-2"' in resp.content


def test_issue_detail_hides_solicitation_tag(basic_issue, auto_login_user):
    basic_issue.desc = "Editor-written text"
    basic_issue.save()
    client, _ = auto_login_user()
    resp = client.get(reverse("issue:detail", kwargs={"slug": basic_issue.slug}))
    assert resp.status_code == HTML_OK_CODE
    assert b'<span class="tag is-info ml-2"' not in resp.content


def test_issue_update_flags_variant_errors_at_top(auto_login_user, basic_issue):
    Variant.objects.create(issue=basic_issue, name="Variant")  # No image, so it's invalid.
    client, _ = auto_login_user()
    variant = basic_issue.variants.get()
    data = {
        "series": basic_issue.series.pk,
        "number": basic_issue.number,
        "cover_date": basic_issue.cover_date,
        "rating": basic_issue.rating.pk,
        **{
            f"{prefix}-{field}": "0"
            for prefix in ("credits", "attribution")
            for field in ("TOTAL_FORMS", "INITIAL_FORMS")
        },
        "variants-TOTAL_FORMS": "1",
        "variants-INITIAL_FORMS": "1",
        "variants-0-id": variant.pk,
        "variants-0-issue": basic_issue.pk,
        "variants-0-name": "Variant",
    }

    resp = client.post(reverse("issue:update", kwargs={"slug": basic_issue.slug}), data=data)

    assert resp.status_code == HTML_OK_CODE
    content = resp.content.decode()
    summary = content[content.index('id="section-errors"') :]
    summary = summary[: summary.index("</ul>")]
    assert 'href="#section-variants"' in summary
    assert 'href="#section-credits"' not in summary


def test_issue_update_flags_primary_errors_at_top(auto_login_user, basic_issue):
    client, _ = auto_login_user()
    data = {
        "series": basic_issue.series.pk,
        "number": basic_issue.number,
        "cover_date": basic_issue.cover_date,
        "rating": basic_issue.rating.pk,
        "sku": "NOT-VALID",  # SKUs must be alphanumeric.
        **{
            f"{prefix}-{field}": "0"
            for prefix in ("credits", "variants", "attribution")
            for field in ("TOTAL_FORMS", "INITIAL_FORMS")
        },
    }

    resp = client.post(reverse("issue:update", kwargs={"slug": basic_issue.slug}), data=data)

    assert resp.status_code == HTML_OK_CODE
    assert resp.context["form"].errors["sku"]
    content = resp.content.decode()
    summary = content[content.index('id="section-errors"') :]
    summary = summary[: summary.index("</ul>")]
    assert 'href="#section-primary"' in summary
    assert 'href="#section-variants"' not in summary


def test_issue_update_form_has_no_error_summary(auto_login_user, basic_issue):
    client, _ = auto_login_user()
    resp = client.get(reverse("issue:update", kwargs={"slug": basic_issue.slug}))
    assert resp.status_code == HTML_OK_CODE
    assert b'id="section-errors"' not in resp.content

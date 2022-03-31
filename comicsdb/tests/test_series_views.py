import pytest
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed

from comicsdb.forms.series import SeriesForm
from comicsdb.models import Series, SeriesType
from comicsdb.models.attribution import Attribution

HTML_OK_CODE = 200
HTML_REDIRECT_CODE = 302

PAGINATE_TEST_VAL = 35
PAGINATE_DEFAULT_VAL = 28
PAGINATE_DIFF_VAL = PAGINATE_TEST_VAL - PAGINATE_DEFAULT_VAL


@pytest.fixture
def list_of_series(create_user, dc_comics):
    user = create_user()
    series_type = SeriesType.objects.create(name="Ongoing Series")
    for pub_num in range(PAGINATE_TEST_VAL):
        Series.objects.create(
            name=f"Series {pub_num}",
            slug=f"series-{pub_num}",
            sort_name=f"Series {pub_num}",
            year_began=2018,
            publisher=dc_comics,
            volume=f"{pub_num}",
            series_type=series_type,
            edited_by=user,
        )


def test_series_search_view_url_exists_at_desired_location(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get("/series/search")
    assert resp.status_code == HTML_OK_CODE


def test_series_search_view_url_accessible_by_name(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("series:search"))
    assert resp.status_code == HTML_OK_CODE


def test_series_search_view_uses_correct_template(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("series:search"))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "comicsdb/series_list.html")


def test_series_search_pagination_is_thirty(auto_login_user, list_of_series):
    client, _ = auto_login_user()
    resp = client.get("/series/search?q=seri")
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["series_list"]) == PAGINATE_DEFAULT_VAL


def test_series_search_lists_all_series(auto_login_user, list_of_series):
    client, _ = auto_login_user()
    # Get second page and confirm it has (exactly) remaining 5 items
    resp = client.get("/series/search?page=2&q=ser")
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["series_list"]) == PAGINATE_DIFF_VAL


def test_series_listview_url_exists_at_desired_location(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get("/series/")
    assert resp.status_code == HTML_OK_CODE


def test_series_listview_url_accessible_by_name(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("series:list"))
    assert resp.status_code == HTML_OK_CODE


def test_series_listview_uses_correct_template(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("series:list"))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "comicsdb/series_list.html")


def test_series_listpagination_is_thirty(auto_login_user, list_of_series):
    client, _ = auto_login_user()
    resp = client.get(reverse("series:list"))
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["series_list"]) == PAGINATE_DEFAULT_VAL


def test_series_listlists_second_page(auto_login_user, list_of_series):
    # Get second page and confirm it has (exactly) remaining 7 items
    client, _ = auto_login_user()
    resp = client.get(reverse("series:list") + "?page=2")
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["series_list"]) == PAGINATE_DIFF_VAL


def test_valid_form(dc_comics, cancelled_type):
    form = SeriesForm(
        data={
            "name": "Batman",
            "sort_name": "Batman",
            "slug": "batman",
            "volume": 3,
            "year_began": 2017,
            "year_end": "",
            "series_type": cancelled_type,
            "publisher": dc_comics,
            "desc": "The Dark Knight.",
        }
    )
    assert form.is_valid() is True


def test_form_invalid(dc_comics, cancelled_type):
    form = SeriesForm(
        data={
            "name": "",
            "sort_name": "",
            "slug": "bad-data",
            "volume": "",
            "year_began": "",
            "series_type": cancelled_type,
            "publisher": dc_comics,
            "desc": "",
        }
    )
    assert form.is_valid() is False


def test_create_series_view(auto_login_user):
    client, _ = auto_login_user()
    response = client.get(reverse("series:create"))
    assert response.status_code == HTML_OK_CODE
    assertTemplateUsed(response, "comicsdb/model_with_attribution_form.html")


def test_create_series_validform_view(auto_login_user, cancelled_type, dc_comics):
    s_name = "Doom Patrol"
    s_slug = "doom-patrol-2017"
    data = {
        "name": s_name,
        "sort_name": s_name,
        "slug": s_slug,
        "volume": 3,
        "year_began": 2017,
        "year_end": 2018,
        "series_type": cancelled_type.id,
        "publisher": dc_comics.id,
        "desc": "Bunch of Misfits",
        "comicsdb-attribution-content_type-object_id-TOTAL_FORMS": 1,
        "comicsdb-attribution-content_type-object_id-INITIAL_FORMS": 0,
        "comicsdb-attribution-content_type-object_id-0-source": "W",
        "comicsdb-attribution-content_type-object_id-0-url": "https://en.wikipedia.org/wiki/Doom_Patrol",
    }
    client, _ = auto_login_user()
    response = client.post(
        reverse("series:create"),
        data=data,
    )
    assert response.status_code == HTML_REDIRECT_CODE
    assert Series.objects.count() == 1
    assert Attribution.objects.count() == 1
    dp = Series.objects.get(slug=s_slug)
    assert dp.name == s_name
    assert dp.sort_name == s_name
    assert dp.slug == s_slug


def test_series_update_view(auto_login_user, fc_series):
    client, _ = auto_login_user()
    k = {"slug": fc_series.slug}
    response = client.get(reverse("series:update", kwargs=k))
    assert response.status_code == HTML_OK_CODE
    assertTemplateUsed(response, "comicsdb/model_with_attribution_form.html")


# def test_series_update_validform_view(auto_login_user, fc_series, cancelled_type, dc_comics):
#     client, _ = auto_login_user()
#     k = {"slug": fc_series.slug}
#     series_count = Series.objects.count()
#     response = client.post(
#         reverse("series:update", kwargs=k),
#         {
#             "name": "Final Crisis",
#             "sort_name": "Final Crisis",
#             "slug": fc_series.slug,
#             "volume": 3,
#             "year_began": 2017,
#             "year_end": "",
#             "series_type": cancelled_type.id,
#             "publisher": dc_comics.id,
#             "desc": "Blah, Blah.",
#         },
#     )
#     assert response.status_code == HTML_REDIRECT_CODE
#     assert Series.objects.count() == series_count

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

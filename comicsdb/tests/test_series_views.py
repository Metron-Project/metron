from django.urls import reverse

from comicsdb.forms.series import SeriesForm
from comicsdb.models import Publisher, Series, SeriesType

from .case_base import TestCaseBase

HTML_OK_CODE = 200

PAGINATE_TEST_VAL = 35
PAGINATE_DEFAULT_VAL = 28
PAGINATE_DIFF_VAL = PAGINATE_TEST_VAL - PAGINATE_DEFAULT_VAL


class SeriesSearchViewsTest(TestCaseBase):
    @classmethod
    def setUpTestData(cls):
        user = cls._create_user()

        cls.publisher = Publisher.objects.create(name="DC", slug="dc", edited_by=user)
        series_type = SeriesType.objects.create(name="Ongoing Series")
        for pub_num in range(PAGINATE_TEST_VAL):
            Series.objects.create(
                name=f"Series {pub_num}",
                slug=f"series-{pub_num}",
                sort_name=f"Series {pub_num}",
                year_began=2018,
                publisher=cls.publisher,
                series_type=series_type,
                edited_by=user,
            )

    def setUp(self):
        self._client_login()

    def test_view_url_exists_at_desired_location(self):
        resp = self.client.get("/series/search")
        self.assertEqual(resp.status_code, HTML_OK_CODE)

    def test_view_url_accessible_by_name(self):
        resp = self.client.get(reverse("series:search"))
        self.assertEqual(resp.status_code, HTML_OK_CODE)

    def test_view_uses_correct_template(self):
        resp = self.client.get(reverse("series:search"))
        self.assertEqual(resp.status_code, HTML_OK_CODE)
        self.assertTemplateUsed(resp, "comicsdb/series_list.html")

    def test_pagination_is_thirty(self):
        resp = self.client.get("/series/search?q=seri")
        self.assertEqual(resp.status_code, HTML_OK_CODE)
        self.assertTrue("is_paginated" in resp.context)
        self.assertTrue(resp.context["is_paginated"] == True)
        self.assertTrue(len(resp.context["series_list"]) == PAGINATE_DEFAULT_VAL)

    def test_lists_all_series(self):
        # Get second page and confirm it has (exactly) remaining 5 items
        resp = self.client.get("/series/search?page=2&q=ser")
        self.assertEqual(resp.status_code, HTML_OK_CODE)
        self.assertTrue("is_paginated" in resp.context)
        self.assertTrue(resp.context["is_paginated"] == True)
        self.assertTrue(len(resp.context["series_list"]) == PAGINATE_DIFF_VAL)


class SeriesListViewTest(TestCaseBase):
    @classmethod
    def setUpTestData(cls):
        user = cls._create_user()

        publisher = Publisher.objects.create(name="DC", slug="dc", edited_by=user)
        series_type = SeriesType.objects.create(name="Ongoing Series")
        for pub_num in range(PAGINATE_TEST_VAL):
            Series.objects.create(
                name=f"Series {pub_num}",
                slug=f"series-{pub_num}",
                sort_name=f"Series {pub_num}",
                year_began=2018,
                publisher=publisher,
                series_type=series_type,
                edited_by=user,
            )

    def setUp(self):
        self._client_login()

    def test_view_url_exists_at_desired_location(self):
        resp = self.client.get("/series/")
        self.assertEqual(resp.status_code, HTML_OK_CODE)

    def test_view_url_accessible_by_name(self):
        resp = self.client.get(reverse("series:list"))
        self.assertEqual(resp.status_code, HTML_OK_CODE)

    def test_view_uses_correct_template(self):
        resp = self.client.get(reverse("series:list"))
        self.assertEqual(resp.status_code, HTML_OK_CODE)
        self.assertTemplateUsed(resp, "comicsdb/series_list.html")

    def test_pagination_is_thirty(self):
        resp = self.client.get(reverse("series:list"))
        self.assertEqual(resp.status_code, HTML_OK_CODE)
        self.assertTrue("is_paginated" in resp.context)
        self.assertTrue(resp.context["is_paginated"] == True)
        self.assertTrue(len(resp.context["series_list"]) == PAGINATE_DEFAULT_VAL)

    def test_lists_second_page(self):
        # Get second page and confirm it has (exactly) remaining 7 items
        resp = self.client.get(reverse("series:list") + "?page=2")
        self.assertEqual(resp.status_code, HTML_OK_CODE)
        self.assertTrue("is_paginated" in resp.context)
        self.assertTrue(resp.context["is_paginated"] == True)
        self.assertTrue(len(resp.context["series_list"]) == PAGINATE_DIFF_VAL)


class TestSeriesForm(TestCaseBase):
    @classmethod
    def setUpTestData(cls):
        user = cls._create_user()

        cls.series_type = SeriesType.objects.create(name="Ongoing Series")
        cls.publisher = Publisher.objects.create(name="DC", slug="dc", edited_by=user)

    def setUp(self):
        self._client_login()

    def test_valid_form(self):
        form = SeriesForm(
            data={
                "name": "Batman",
                "sort_name": "Batman",
                "slug": "batman",
                "volume": 3,
                "year_began": 2017,
                "year_end": "",
                "series_type": self.series_type.id,
                "publisher": self.publisher.id,
                "desc": "The Dark Knight.",
            }
        )
        self.assertTrue(form.is_valid())

    def test_form_invalid(self):
        form = SeriesForm(
            data={
                "name": "",
                "sort_name": "",
                "slug": "bad-data",
                "volume": "",
                "year_began": "",
                "series_type": self.series_type.id,
                "publisher": self.publisher.id,
                "desc": "",
            }
        )
        self.assertFalse(form.is_valid())

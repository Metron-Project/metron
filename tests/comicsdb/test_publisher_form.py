import pytest

from comicsdb.forms.publisher import PublisherForm


class TestPublisherFormCountry:
    @pytest.fixture
    def base_data(self):
        return {
            "name": "Test Publisher",
            "founded": 1990,
        }

    @pytest.mark.parametrize("country", ["US", "GB"])
    def test_allowed_countries(self, base_data, country):
        base_data["country"] = country
        form = PublisherForm(data=base_data)
        assert "country" not in form.errors

    def test_disallowed_country_raises_error(self, base_data):
        base_data["country"] = "CA"
        form = PublisherForm(data=base_data)
        assert "country" in form.errors

    def test_disallowed_country_error_message(self, base_data):
        base_data["country"] = "DE"
        form = PublisherForm(data=base_data)
        assert "Currently only US and UK Publishers are supported" in form.errors["country"]

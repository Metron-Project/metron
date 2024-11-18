import pytest

from comicsdb.forms.issue import IssueForm
from comicsdb.models import Rating


@pytest.mark.django_db
class TestIssueForm:
    @pytest.fixture
    def rating(self):
        return Rating.objects.create(name="Test Rating")

    @pytest.fixture
    def issue_data(self, fc_series, rating):
        return {
            "series": fc_series.id,
            "number": "1",
            "title": "Test Title",
            "name": "Test Name",
            "cover_date": "2023-01-01",
            "store_date": "2023-01-02",
            "rating": rating.id,
            "price": "9.99",
            "sku": "SKU123",
            "isbn": "0-87135-814-X",
            "upc": "123456789012",
            "page": "1",
            "cv_id": "123",
            "desc": "Test Description",
            "characters": [],
            "teams": [],
            "arcs": [],
            "universes": [],
            "reprints": [],
            "image": None,
        }

    @pytest.mark.parametrize(
        ("field", "value", "expected"),
        [
            ("sku", "SKU123", "SKU123"),
            ("isbn", "0-87135-814-X", "087135814X"),
            ("upc", "123456789012", "123456789012"),
        ],
        ids=[
            "valid_sku",
            "valid_isbn",
            "valid_upc",
        ],
    )
    def test_clean_fields_valid(self, issue_data, field, value, expected):
        # Arrange
        issue_data[field] = value
        form = IssueForm(data=issue_data)

        # Act
        form.is_valid()
        result = form.cleaned_data[field]

        # Assert
        assert result == expected

    @pytest.mark.parametrize(
        ("field", "value", "error_message"),
        [
            ("sku", "SKU 123", "SKU must be alphanumeric. No spaces or hyphens allowed."),
            ("isbn", "invalid_isbn", "ISBN is not a valid ISBN-10 or ISBN-13."),
            ("upc", "UPC 123", "UPC must be numeric. No spaces or hyphens allowed."),
            ("title", "Test Title", "Collection Title field is not allowed for this series.."),
        ],
        ids=[
            "invalid_sku",
            "invalid_isbn",
            "invalid_upc",
            "invalid_title",
        ],
    )
    def test_clean_fields_invalid(self, issue_data, field, value, error_message):
        # Arrange
        issue_data[field] = value
        form = IssueForm(data=issue_data)

        # Act
        form.is_valid()

        # Assert
        assert error_message in form.errors[field]

    def test_init_sets_name_delimiter(self, issue_data):
        # Arrange
        form = IssueForm(data=issue_data)

        # Act
        delimiter = form.fields["name"].delimiter

        # Assert
        assert delimiter == ";"

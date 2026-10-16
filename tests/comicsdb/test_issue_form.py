from datetime import date

import pytest
from django.contrib import admin
from django.forms.models import model_to_dict

from comicsdb.forms.issue import IssueForm
from comicsdb.forms.variant import VariantFormset
from comicsdb.models import Issue, Rating

LEGACY_UPC = "0714860246207"


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
            ("cover_date", date(2023, 1, 1), date(2023, 1, 1)),
            ("store_date", date(2023, 1, 1), date(2023, 1, 1)),
        ],
        ids=["valid_sku", "valid_isbn", "valid_upc", "valid_cover_date", "valid_store_date"],
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
            (
                "upc",
                "12345678901",
                "UPC must be 12 or 13 digits, optionally followed by a 2 or 5 digit add-on.",
            ),
            ("upc", "123456789013", "UPC check digit is invalid."),
            ("title", "Test Title", "Collection Title field is not allowed for this series.."),
            ("cover_date", date(412, 1, 1), "Date has a non-valid year."),
            ("store_date", date(412, 1, 1), "Date has a non-valid year."),
        ],
        ids=[
            "invalid_sku",
            "invalid_isbn",
            "invalid_upc",
            "invalid_upc_length",
            "invalid_upc_check_digit",
            "invalid_title",
            "invalid_cover_date",
            "invalid_store_date",
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

    @pytest.mark.parametrize(
        ("cover_date", "valid"),
        [("1976-07-01", True), ("1993-01-01", False)],
        ids=["before_cutoff", "from_cutoff"],
    )
    def test_legacy_upc_check_digit_depends_on_cover_date(self, issue_data, cover_date, valid):
        issue_data.update(cover_date=cover_date, store_date="", upc=LEGACY_UPC)
        form = IssueForm(data=issue_data)

        form.is_valid()

        assert ("upc" not in form.errors) is valid

    @pytest.mark.parametrize(
        ("cover_date", "valid"),
        [(date(1976, 7, 1), True), (date(2023, 1, 1), False)],
        ids=["before_cutoff", "from_cutoff"],
    )
    def test_variant_legacy_upc_uses_issue_cover_date(self, basic_issue, cover_date, valid):
        Issue.objects.filter(pk=basic_issue.pk).update(cover_date=cover_date)
        basic_issue.refresh_from_db()
        data = {
            "variants-TOTAL_FORMS": "1",
            "variants-INITIAL_FORMS": "0",
            "variants-0-name": "Variant",
            "variants-0-upc": LEGACY_UPC,
        }
        formset = VariantFormset(
            data, {"variants-0-image": None}, instance=basic_issue, prefix="variants"
        )

        formset.is_valid()

        assert ("upc" not in formset.forms[0].errors) is valid

    def test_init_sets_name_delimiter(self, issue_data):
        # Arrange
        form = IssueForm(data=issue_data)

        # Act
        delimiter = form.fields["name"].delimiter

        # Assert
        assert delimiter == ";"


@pytest.mark.django_db
class TestIssueFormSolicitationFlag:
    @pytest.fixture
    def issue_data(self, fc_series):
        return {
            "series": fc_series.id,
            "number": "1",
            "cover_date": "2023-01-01",
            "rating": Rating.objects.create(name="Test Rating").id,
            "desc": "Solicitation text",
            "desc_is_solicitation": True,
        }

    @pytest.fixture
    def solicited_issue(self, basic_issue):
        basic_issue.desc = "Solicitation text"
        basic_issue.desc_is_solicitation = True
        basic_issue.save()
        return basic_issue

    def _cleaned_flag(self, data, instance=None):
        form = IssueForm(data=data, instance=instance)
        assert form.is_valid(), form.errors
        return form.cleaned_data["desc_is_solicitation"]

    def test_unchanged_desc_keeps_flag(self, issue_data, solicited_issue):
        assert self._cleaned_flag(issue_data, solicited_issue) is True

    def test_crlf_resubmission_of_lf_desc_keeps_flag(self, issue_data, solicited_issue):
        solicited_issue.desc = "Line one\nLine two"
        solicited_issue.save()
        issue_data["desc"] = "Line one\r\nLine two"

        assert self._cleaned_flag(issue_data, solicited_issue) is True

    def test_changed_desc_clears_flag(self, issue_data, solicited_issue):
        issue_data["desc"] = "Rewritten by an editor"

        assert self._cleaned_flag(issue_data, solicited_issue) is False

    def test_changed_desc_keeps_flag_when_kept(self, issue_data, solicited_issue):
        issue_data.update(desc="Updated solicitation text", desc_solicitation_kept="True")

        assert self._cleaned_flag(issue_data, solicited_issue) is True

    def test_changed_desc_can_be_newly_flagged(self, issue_data, basic_issue):
        issue_data["desc"] = "New solicitation text"

        assert self._cleaned_flag(issue_data, basic_issue) is True

    def test_flag_can_be_unchecked(self, issue_data, solicited_issue):
        del issue_data["desc_is_solicitation"]

        assert self._cleaned_flag(issue_data, solicited_issue) is False

    def test_new_issue_can_be_flagged(self, issue_data):
        assert self._cleaned_flag(issue_data) is True

    def _admin_cleaned_flag(self, rf, create_staff_user, issue, **changes):
        request = rf.get("/")
        request.user = create_staff_user
        form_class = admin.site._registry[Issue].get_form(request, issue)
        data = {
            key: value
            for key, value in model_to_dict(issue).items()
            if value is not None and key not in {"image", "price"}
        }
        data["rating"] = Rating.objects.create(name="Test Rating").id
        data.update(changes)
        form = form_class(data=data, instance=issue)
        assert form.is_valid(), form.errors
        return form.cleaned_data["desc_is_solicitation"]

    def test_admin_changed_desc_clears_flag(self, rf, create_staff_user, solicited_issue):
        flag = self._admin_cleaned_flag(
            rf, create_staff_user, solicited_issue, desc="Rewritten by an admin"
        )

        assert flag is False

    def test_admin_other_change_keeps_flag(self, rf, create_staff_user, solicited_issue):
        flag = self._admin_cleaned_flag(rf, create_staff_user, solicited_issue, page=32)

        assert flag is True

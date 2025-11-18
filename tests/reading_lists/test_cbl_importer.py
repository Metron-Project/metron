"""Tests for CBL importer functionality."""

import tempfile
from datetime import date
from pathlib import Path

import pytest

from comicsdb.models.issue import Issue
from reading_lists.cbl_importer import (
    CBLImportError,
    CBLParseError,
    import_cbl_file,
    parse_cbl_file,
)
from reading_lists.models import ReadingList, ReadingListItem


@pytest.fixture
def simple_cbl_content():
    """Create a simple valid CBL XML content."""
    return """<?xml version="1.0" encoding="utf-8"?>
<ReadingList xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<Name>Test Reading List</Name>
<NumIssues>3</NumIssues>
<Books>
<Book Series="Crisis on Infinite Earths" Number="1" Volume="1985" Year="1985">
<Database Name="cv" Series="3441" Issue="25335" />
</Book>
<Book Series="The Fury of Firestorm" Number="41" Volume="1982" Year="1985">
<Database Name="cv" Series="3115" Issue="26035" />
</Book>
<Book Series="Batman" Number="389" Volume="1940" Year="1985">
<Database Name="metron" Series="1" Issue="1" />
</Book>
</Books>
<Matchers />
</ReadingList>
"""


@pytest.fixture
def simple_cbl_file(tmp_path, simple_cbl_content):
    """Create a temporary CBL file with simple content."""
    cbl_file = tmp_path / "test_list.cbl"
    cbl_file.write_text(simple_cbl_content)
    return cbl_file


@pytest.fixture
def invalid_cbl_file(tmp_path):
    """Create a temporary CBL file with invalid XML."""
    cbl_file = tmp_path / "invalid.cbl"
    cbl_file.write_text("This is not valid XML")
    return cbl_file


@pytest.fixture
def missing_name_cbl_file(tmp_path):
    """Create a temporary CBL file missing the Name element."""
    cbl_file = tmp_path / "missing_name.cbl"
    cbl_file.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<ReadingList>
<NumIssues>0</NumIssues>
<Books></Books>
</ReadingList>
"""
    )
    return cbl_file


@pytest.fixture
def issue_with_cv_id(create_user, reading_list_series):
    """Create an issue with a ComicVine ID."""
    user = create_user()
    return Issue.objects.create(
        series=reading_list_series,
        number="1",
        slug="test-series-cv-1",
        cover_date=date(2020, 1, 1),
        cv_id=25335,  # ComicVine ID from our test CBL file
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def issue_with_metron_id(create_user, reading_list_series):
    """Create an issue with a known Metron ID (primary key)."""
    user = create_user()
    # Create with a specific ID by using get_or_create
    return Issue.objects.create(
        series=reading_list_series,
        number="389",
        slug="test-series-metron-389",
        cover_date=date(2020, 1, 1),
        edited_by=user,
        created_by=user,
    )


class TestParseCBLFile:
    """Tests for the parse_cbl_file function."""

    def test_parse_valid_cbl_file(self, simple_cbl_file):
        """Test parsing a valid CBL file."""
        cbl_data = parse_cbl_file(simple_cbl_file)

        assert cbl_data.name == "Test Reading List"
        assert cbl_data.num_issues == 3
        assert len(cbl_data.books) == 3

        # Check first book
        first_book = cbl_data.books[0]
        assert first_book.series == "Crisis on Infinite Earths"
        assert first_book.number == "1"
        assert first_book.volume == "1985"
        assert first_book.year == "1985"
        assert first_book.database_name == "cv"
        assert first_book.database_series_id == "3441"
        assert first_book.database_issue_id == "25335"
        assert first_book.order == 1

        # Check last book (metron database)
        last_book = cbl_data.books[2]
        assert last_book.database_name == "metron"
        assert last_book.database_issue_id == "1"
        assert last_book.order == 3

    def test_parse_nonexistent_file(self):
        """Test parsing a file that doesn't exist."""
        with pytest.raises(FileNotFoundError):
            parse_cbl_file("/nonexistent/file.cbl")

    def test_parse_invalid_extension(self, tmp_path):
        """Test parsing a file with wrong extension."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Some content")

        with pytest.raises(CBLParseError, match=r"must have \.cbl extension"):
            parse_cbl_file(txt_file)

    def test_parse_invalid_xml(self, invalid_cbl_file):
        """Test parsing invalid XML."""
        with pytest.raises(CBLParseError, match="Failed to parse XML"):
            parse_cbl_file(invalid_cbl_file)

    def test_parse_missing_name(self, missing_name_cbl_file):
        """Test parsing CBL file without Name element."""
        with pytest.raises(CBLParseError, match="missing required 'Name' element"):
            parse_cbl_file(missing_name_cbl_file)


class TestImportCBLFile:
    """Tests for the import_cbl_file function."""

    def test_import_with_cv_id(self, simple_cbl_file, reading_list_user, issue_with_cv_id):
        """Test importing a CBL file with ComicVine IDs."""
        result = import_cbl_file(
            simple_cbl_file,
            user=reading_list_user,
            attribution_source=ReadingList.AttributionSource.LOCG,
        )

        assert isinstance(result.reading_list, ReadingList)
        assert result.reading_list.name == "Test Reading List"
        assert result.reading_list.user == reading_list_user
        assert result.reading_list.attribution_source == ReadingList.AttributionSource.LOCG
        assert result.issues_added == 1  # Only one issue exists in DB (issue_with_cv_id)
        # At least one issue should not be found (the cv ID 26035)
        # The metron ID 1 might or might not be found depending on other fixtures
        assert len(result.issues_not_found) >= 1

    def test_import_with_metron_id(self, simple_cbl_file, reading_list_user, issue_with_metron_id):
        """Test importing a CBL file with Metron IDs."""
        # Update the CBL file to use the actual metron ID
        cbl_content = f"""<?xml version="1.0" encoding="utf-8"?>
<ReadingList>
<Name>Metron Test List</Name>
<NumIssues>1</NumIssues>
<Books>
<Book Series="Batman" Number="389" Volume="1940" Year="1985">
<Database Name="metron" Series="1" Issue="{issue_with_metron_id.id}" />
</Book>
</Books>
</ReadingList>
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cbl", delete=False) as f:
            f.write(cbl_content)
            temp_path = Path(f.name)

        try:
            result = import_cbl_file(temp_path, user=reading_list_user)

            assert result.reading_list.name == "Metron Test List"
            assert result.issues_added == 1
            assert len(result.issues_not_found) == 0

            # Verify the reading list item was created with correct order
            reading_list_item = ReadingListItem.objects.get(
                reading_list=result.reading_list, issue=issue_with_metron_id
            )
            assert reading_list_item.order == 1
        finally:
            temp_path.unlink()

    def test_import_private_list(self, simple_cbl_file, reading_list_user):
        """Test importing a private reading list."""
        result = import_cbl_file(simple_cbl_file, user=reading_list_user, is_private=True)

        assert result.reading_list.is_private

    def test_import_with_attribution_url(self, simple_cbl_file, reading_list_user):
        """Test importing with attribution URL."""
        attribution_url = "https://example.com/reading-order"
        result = import_cbl_file(
            simple_cbl_file, user=reading_list_user, attribution_url=attribution_url
        )

        assert result.reading_list.attribution_url == attribution_url

    def test_import_duplicate_name(self, simple_cbl_file, reading_list_user):
        """Test importing a CBL file when a list with the same name exists."""
        # Create a reading list with the same name
        ReadingList.objects.create(user=reading_list_user, name="Test Reading List")

        # Try to import the CBL file
        with pytest.raises(CBLImportError, match="already exists"):
            import_cbl_file(simple_cbl_file, user=reading_list_user)

    def test_import_all_issues_not_found(self, simple_cbl_file, reading_list_user):
        """Test importing when no issues are found in the database."""
        result = import_cbl_file(simple_cbl_file, user=reading_list_user)

        assert result.issues_added == 0
        assert len(result.issues_not_found) == 3
        # Reading list should still be created
        assert result.reading_list is not None
        assert result.reading_list.reading_list_items.count() == 0

    def test_import_mixed_databases(
        self, reading_list_user, issue_with_cv_id, issue_with_metron_id
    ):
        """Test importing a CBL file with both CV and Metron IDs."""
        cbl_content = f"""<?xml version="1.0" encoding="utf-8"?>
<ReadingList>
<Name>Mixed Database List</Name>
<NumIssues>2</NumIssues>
<Books>
<Book Series="Crisis on Infinite Earths" Number="1" Volume="1985" Year="1985">
<Database Name="cv" Series="3441" Issue="{issue_with_cv_id.cv_id}" />
</Book>
<Book Series="Batman" Number="389" Volume="1940" Year="1985">
<Database Name="metron" Series="1" Issue="{issue_with_metron_id.id}" />
</Book>
</Books>
</ReadingList>
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cbl", delete=False) as f:
            f.write(cbl_content)
            temp_path = Path(f.name)

        try:
            result = import_cbl_file(temp_path, user=reading_list_user)

            assert result.issues_added == 2
            assert len(result.issues_not_found) == 0

            # Verify both issues were added in correct order
            items = result.reading_list.reading_list_items.order_by("order")
            assert items.count() == 2
            assert items[0].issue == issue_with_cv_id
            assert items[0].order == 1
            assert items[1].issue == issue_with_metron_id
            assert items[1].order == 2
        finally:
            temp_path.unlink()

    def test_import_invalid_cv_id(self, tmp_path, reading_list_user):
        """Test importing with invalid ComicVine ID."""
        cbl_content = """<?xml version="1.0" encoding="utf-8"?>
<ReadingList>
<Name>Invalid ID List</Name>
<NumIssues>1</NumIssues>
<Books>
<Book Series="Test" Number="1" Volume="2020" Year="2020">
<Database Name="cv" Series="123" Issue="not-a-number" />
</Book>
</Books>
</ReadingList>
"""
        cbl_file = tmp_path / "invalid_id.cbl"
        cbl_file.write_text(cbl_content)

        result = import_cbl_file(cbl_file, user=reading_list_user)

        # Invalid ID should be skipped, not marked as not found
        assert result.issues_added == 0
        assert len(result.issues_not_found) == 0
        assert len(result.issues_skipped) == 1
        _, reason = result.issues_skipped[0]
        assert "Invalid ComicVine ID" in reason

    def test_import_unsupported_database(self, tmp_path, reading_list_user):
        """Test importing with unsupported database name."""
        cbl_content = """<?xml version="1.0" encoding="utf-8"?>
<ReadingList>
<Name>Unsupported Database List</Name>
<NumIssues>1</NumIssues>
<Books>
<Book Series="Test" Number="1" Volume="2020" Year="2020">
<Database Name="gcd" Series="123" Issue="456" />
</Book>
</Books>
</ReadingList>
"""
        cbl_file = tmp_path / "unsupported_db.cbl"
        cbl_file.write_text(cbl_content)

        result = import_cbl_file(cbl_file, user=reading_list_user)

        assert result.issues_added == 0
        assert len(result.issues_skipped) == 1
        skipped_book, reason = result.issues_skipped[0]
        assert skipped_book.database_name == "gcd"
        assert "Unsupported database" in reason

    def test_import_duplicate_issues(self, tmp_path, reading_list_user, issue_with_cv_id):
        """Test importing a CBL file with duplicate issue entries."""
        # Create a CBL file with the same issue appearing twice
        cbl_content = f"""<?xml version="1.0" encoding="utf-8"?>
<ReadingList>
<Name>Duplicate Issues List</Name>
<NumIssues>2</NumIssues>
<Books>
<Book Series="Crisis on Infinite Earths" Number="1" Volume="1985" Year="1985">
<Database Name="cv" Series="3441" Issue="{issue_with_cv_id.cv_id}" />
</Book>
<Book Series="Crisis on Infinite Earths" Number="1" Volume="1985" Year="1985">
<Database Name="cv" Series="3441" Issue="{issue_with_cv_id.cv_id}" />
</Book>
</Books>
</ReadingList>
"""
        cbl_file = tmp_path / "duplicates.cbl"
        cbl_file.write_text(cbl_content)

        result = import_cbl_file(cbl_file, user=reading_list_user)

        # First occurrence should be added, second should be skipped
        assert result.issues_added == 1
        assert len(result.issues_skipped) == 1
        _, reason = result.issues_skipped[0]
        assert "already in reading list" in reason.lower()

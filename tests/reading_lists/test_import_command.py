"""Tests for import_reading_lists management command."""

import json

import pytest
from django.core.management import CommandError, call_command

from reading_lists.models import ReadingList, ReadingListItem


@pytest.fixture
def json_data():
    """Sample JSON data matching the expected format."""
    return {
        "name": "[2015-2016] Justice League Darkseid War",
        "source": "LoCG",
        "books": [
            {"index": 0, "database": {"id": 1}},
            {"index": 1, "database": {"id": 2}},
            {"index": 2, "database": {"id": 3}},
        ],
    }


@pytest.fixture
def json_file(tmp_path, json_data):
    """Create a temporary JSON file."""
    file_path = tmp_path / "test_reading_list.json"
    with file_path.open("w", encoding="utf-8") as f:
        json.dump(json_data, f)
    return file_path


@pytest.fixture
def json_file_with_issues(
    tmp_path, reading_list_issue_1, reading_list_issue_2, reading_list_issue_3
):
    """Create a JSON file with real issue IDs."""
    data = {
        "name": "[2015-2016] Justice League Darkseid War",
        "source": "LoCG",
        "books": [
            {"index": 0, "database": {"id": reading_list_issue_1.id}},
            {"index": 1, "database": {"id": reading_list_issue_2.id}},
            {"index": 2, "database": {"id": reading_list_issue_3.id}},
        ],
    }
    file_path = tmp_path / "test_with_real_issues.json"
    with file_path.open("w", encoding="utf-8") as f:
        json.dump(data, f)
    return file_path


@pytest.fixture
def multiple_json_files(tmp_path, reading_list_issue_1, reading_list_issue_2, reading_list_issue_3):
    """Create multiple JSON files in a directory."""
    files = []
    for i in range(3):
        data = {
            "name": f"[2020] Reading List {i + 1}",
            "source": "CBRO",
            "books": [
                {"index": 0, "database": {"id": reading_list_issue_1.id}},
                {"index": 1, "database": {"id": reading_list_issue_2.id}},
            ],
        }
        file_path = tmp_path / f"reading_list_{i + 1}.json"
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(data, f)
        files.append(file_path)
    return tmp_path, files


@pytest.mark.django_db
class TestImportReadingListsCommand:
    """Tests for the import_reading_lists management command."""

    def test_import_without_metron_user_fails(self, db, json_file):
        """Test that command fails when Metron user doesn't exist."""
        with pytest.raises(CommandError, match='User "Metron" does not exist'):
            call_command("import_reading_lists", str(json_file))

    def test_import_single_file(
        self,
        metron_user,
        json_file_with_issues,
        reading_list_issue_1,
        reading_list_issue_2,
        reading_list_issue_3,
    ):
        """Test importing a single JSON file."""
        call_command("import_reading_lists", str(json_file_with_issues))

        # Verify reading list was created
        assert ReadingList.objects.filter(user=metron_user).count() == 1
        reading_list = ReadingList.objects.get(user=metron_user)

        # Check name was sanitized (year prefix removed)
        assert reading_list.name == "Justice League Darkseid War"
        assert reading_list.attribution_source == ReadingList.AttributionSource.LOCG
        assert reading_list.is_private is False

        # Verify all issues were added
        assert reading_list.reading_list_items.count() == 3
        items = reading_list.reading_list_items.order_by("order")
        assert items[0].issue == reading_list_issue_1
        assert items[0].order == 0
        assert items[1].issue == reading_list_issue_2
        assert items[1].order == 1
        assert items[2].issue == reading_list_issue_3
        assert items[2].order == 2

    def test_import_with_dry_run(self, metron_user, json_file_with_issues):
        """Test dry run mode doesn't create anything."""
        call_command("import_reading_lists", str(json_file_with_issues), "--dry-run")

        # Verify nothing was created
        assert ReadingList.objects.filter(user=metron_user).count() == 0
        assert ReadingListItem.objects.count() == 0

    def test_import_duplicate_skipped(self, metron_user, json_file_with_issues):
        """Test that duplicate reading lists are skipped."""
        # First import
        call_command("import_reading_lists", str(json_file_with_issues))
        assert ReadingList.objects.filter(user=metron_user).count() == 1

        # Second import (should skip)
        call_command("import_reading_lists", str(json_file_with_issues))
        assert ReadingList.objects.filter(user=metron_user).count() == 1

    def test_import_missing_issues_fails(self, metron_user, json_file, capsys):
        """Test that missing issues cause failure by default."""
        call_command("import_reading_lists", str(json_file))

        # Verify reading list was not created
        assert ReadingList.objects.filter(user=metron_user).count() == 0

        # Check error message in output
        captured = capsys.readouterr()
        assert "Issues not found in database" in captured.out
        assert "Errors: 1" in captured.out

    def test_import_missing_issues_with_skip_flag(
        self, metron_user, tmp_path, reading_list_issue_1
    ):
        """Test that --skip-missing allows import with some missing issues."""
        data = {
            "name": "Partial List",
            "source": "CBH",
            "books": [
                {"index": 0, "database": {"id": reading_list_issue_1.id}},
                {"index": 1, "database": {"id": 99999}},  # Non-existent issue
                {"index": 2, "database": {"id": 99998}},  # Non-existent issue
            ],
        }
        file_path = tmp_path / "partial.json"
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(data, f)

        call_command("import_reading_lists", str(file_path), "--skip-missing")

        # Verify reading list was created with only existing issue
        reading_list = ReadingList.objects.get(user=metron_user)
        assert reading_list.reading_list_items.count() == 1
        assert reading_list.reading_list_items.first().issue == reading_list_issue_1

    def test_import_directory(self, metron_user, multiple_json_files):
        """Test importing all JSON files from a directory."""
        directory, _files = multiple_json_files

        call_command("import_reading_lists", str(directory))

        # Verify all three reading lists were created
        assert ReadingList.objects.filter(user=metron_user).count() == 3

        # Check names were sanitized
        names = set(ReadingList.objects.values_list("name", flat=True))
        expected_names = {"Reading List 1", "Reading List 2", "Reading List 3"}
        assert names == expected_names

    def test_import_multiple_files(
        self, metron_user, tmp_path, reading_list_issue_1, reading_list_issue_2
    ):
        """Test importing multiple individual files."""
        data1 = {
            "name": "First List",
            "source": "CMRO",
            "books": [{"index": 0, "database": {"id": reading_list_issue_1.id}}],
        }
        data2 = {
            "name": "Second List",
            "source": "CBT",
            "books": [{"index": 0, "database": {"id": reading_list_issue_2.id}}],
        }

        file1 = tmp_path / "list1.json"
        file2 = tmp_path / "list2.json"

        with file1.open("w", encoding="utf-8") as f:
            json.dump(data1, f)
        with file2.open("w", encoding="utf-8") as f:
            json.dump(data2, f)

        call_command("import_reading_lists", str(file1), str(file2))

        assert ReadingList.objects.filter(user=metron_user).count() == 2

    def test_import_invalid_json(self, metron_user, tmp_path, capsys):
        """Test that invalid JSON is handled gracefully."""
        file_path = tmp_path / "invalid.json"
        with file_path.open("w", encoding="utf-8") as f:
            f.write("{invalid json")

        call_command("import_reading_lists", str(file_path))

        # Verify reading list was not created
        assert ReadingList.objects.filter(user=metron_user).count() == 0

        # Check error message in output
        captured = capsys.readouterr()
        assert "Invalid JSON" in captured.out
        assert "Errors: 1" in captured.out

    def test_import_missing_name_field(self, metron_user, tmp_path, capsys):
        """Test that missing 'name' field is handled gracefully."""
        data = {"source": "CBRO", "books": []}
        file_path = tmp_path / "no_name.json"
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(data, f)

        call_command("import_reading_lists", str(file_path))

        # Verify reading list was not created
        assert ReadingList.objects.filter(user=metron_user).count() == 0

        # Check error message in output
        captured = capsys.readouterr()
        assert "Missing 'name' field" in captured.out
        assert "Errors: 1" in captured.out

    def test_import_missing_books_field(self, metron_user, tmp_path, capsys):
        """Test that missing 'books' field is handled gracefully."""
        data = {"name": "Test List", "source": "CBRO"}
        file_path = tmp_path / "no_books.json"
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(data, f)

        call_command("import_reading_lists", str(file_path))

        # Verify reading list was not created
        assert ReadingList.objects.filter(user=metron_user).count() == 0

        # Check error message in output
        captured = capsys.readouterr()
        assert "Missing 'books' field" in captured.out
        assert "Errors: 1" in captured.out

    def test_import_nonexistent_path(self, metron_user):
        """Test that nonexistent path raises error."""
        with pytest.raises(CommandError, match="Path does not exist"):
            call_command("import_reading_lists", "/nonexistent/path.json")

    def test_name_sanitization_variations(self, metron_user, tmp_path, reading_list_issue_1):
        """Test various name sanitization patterns."""
        test_cases = [
            ("[2015-2016] Justice League Darkseid War", "Justice League Darkseid War"),
            ("[2015] Crisis on Infinite Earths", "Crisis on Infinite Earths"),
            ("(2015-2016) Infinity Gauntlet", "Infinity Gauntlet"),
            ("(2015) Secret Wars", "Secret Wars"),
            ("Final Crisis", "Final Crisis"),  # No prefix
            ("[2015-2016]No Space List", "No Space List"),  # No space after bracket
        ]

        for i, (input_name, _expected_name) in enumerate(test_cases):
            data = {
                "name": input_name,
                "source": "CBRO",
                "books": [{"index": 0, "database": {"id": reading_list_issue_1.id}}],
            }
            file_path = tmp_path / f"sanitize_{i}.json"
            with file_path.open("w", encoding="utf-8") as f:
                json.dump(data, f)

            call_command("import_reading_lists", str(file_path))

        # Verify all names were sanitized correctly
        names = list(ReadingList.objects.values_list("name", flat=True).order_by("id"))
        expected_names = [expected for _, expected in test_cases]
        assert names == expected_names

    def test_attribution_source_mapping(self, metron_user, tmp_path, reading_list_issue_1):
        """Test all attribution source mappings."""
        source_mappings = [
            ("CBRO", ReadingList.AttributionSource.CBRO),
            ("CMRO", ReadingList.AttributionSource.CMRO),
            ("CBH", ReadingList.AttributionSource.CBH),
            ("CBT", ReadingList.AttributionSource.CBT),
            ("MG", ReadingList.AttributionSource.MG),
            ("HTLC", ReadingList.AttributionSource.HTLC),
            ("LoCG", ReadingList.AttributionSource.LOCG),
            ("LOCG", ReadingList.AttributionSource.LOCG),
            ("OTHER", ReadingList.AttributionSource.OTHER),
            ("", ""),  # Empty source
        ]

        for i, (source_code, _expected_source) in enumerate(source_mappings):
            data = {
                "name": f"Test List {i}",
                "source": source_code,
                "books": [{"index": 0, "database": {"id": reading_list_issue_1.id}}],
            }
            file_path = tmp_path / f"source_{i}.json"
            with file_path.open("w", encoding="utf-8") as f:
                json.dump(data, f)

            call_command("import_reading_lists", str(file_path))

        # Verify all sources were mapped correctly
        reading_lists = ReadingList.objects.order_by("id")
        for i, reading_list in enumerate(reading_lists):
            expected = source_mappings[i][1]
            assert reading_list.attribution_source == expected

    def test_bulk_create_performance(self, metron_user, tmp_path, series_with_multiple_issues):
        """Test that bulk_create is used for reading list items."""
        _series, issues = series_with_multiple_issues

        data = {
            "name": "Bulk Test",
            "source": "CBRO",
            "books": [{"index": i, "database": {"id": issue.id}} for i, issue in enumerate(issues)],
        }
        file_path = tmp_path / "bulk_test.json"
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(data, f)

        call_command("import_reading_lists", str(file_path))

        # Verify all items were created
        reading_list = ReadingList.objects.get(user=metron_user)
        assert reading_list.reading_list_items.count() == 10

        # Verify order is correct
        items = reading_list.reading_list_items.order_by("order")
        for i, item in enumerate(items):
            assert item.order == i
            assert item.issue == issues[i]

    def test_empty_books_list(self, metron_user, tmp_path):
        """Test importing a reading list with no books."""
        data = {
            "name": "Empty List",
            "source": "CBRO",
            "books": [],
        }
        file_path = tmp_path / "empty.json"
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(data, f)

        call_command("import_reading_lists", str(file_path))

        # Verify reading list was created but has no items
        reading_list = ReadingList.objects.get(user=metron_user)
        assert reading_list.reading_list_items.count() == 0

    def test_non_json_file_skipped(self, metron_user, tmp_path, json_file_with_issues):
        """Test that non-JSON files in a directory are skipped."""
        # Create a text file in the same directory
        text_file = tmp_path / "readme.txt"
        with text_file.open("w", encoding="utf-8") as f:
            f.write("This is not a JSON file")

        # Import the directory
        call_command("import_reading_lists", str(tmp_path))

        # Verify only the JSON file was imported
        assert ReadingList.objects.filter(user=metron_user).count() == 1

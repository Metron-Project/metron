"""Utility for importing Comic Book List (.cbl) files into reading lists.

Comic Book List files are XML files that contain ordered lists of comic issues
with external database IDs (ComicVine, Metron, etc.).
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from defusedxml import ElementTree
from django.db import transaction

from comicsdb.models.issue import Issue
from reading_lists.models import ReadingList, ReadingListItem

LOGGER = logging.getLogger(__name__)


@dataclass
class CBLBook:
    """Represents a single book entry from a CBL file."""

    series: str
    number: str
    volume: str
    year: str
    database_name: str
    database_series_id: str
    database_issue_id: str
    order: int


@dataclass
class CBLData:
    """Represents the parsed data from a CBL file."""

    name: str
    num_issues: int
    books: list[CBLBook]


class CBLParseError(Exception):
    """Raised when a CBL file cannot be parsed."""


class CBLImportError(Exception):
    """Raised when a CBL file cannot be imported into a reading list."""


def parse_cbl_file(file_path: str | Path) -> CBLData:
    """Parse a Comic Book List (.cbl) XML file.

    Args:
        file_path: Path to the .cbl file to parse

    Returns:
        CBLData object containing the parsed reading list information

    Raises:
        CBLParseError: If the file cannot be parsed or has invalid structure
        FileNotFoundError: If the file does not exist
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"CBL file not found: {file_path}")

    if not file_path.suffix.lower() == ".cbl":
        raise CBLParseError(f"File must have .cbl extension: {file_path}")

    try:
        tree = ElementTree.parse(file_path)
        root = tree.getroot()
    except ElementTree.ParseError as e:
        raise CBLParseError(f"Failed to parse XML file: {e}") from e

    # Remove namespace if present
    if root.tag.startswith("{"):
        # Extract namespace
        namespace = root.tag[1 : root.tag.index("}")]
        namespace_map = {"": namespace}
    else:
        namespace_map = {}

    def find_text(element, tag):
        """Helper to find element text with optional namespace."""
        if namespace_map:
            found = element.find(f"{{{namespace_map['']}}} {tag}")
        else:
            found = element.find(tag)
        return found.text if found is not None else None

    # Extract metadata
    name_elem = (
        root.find("Name") if not namespace_map else root.find(f"{{{namespace_map['']}}}Name")
    )
    num_issues_elem = (
        root.find("NumIssues")
        if not namespace_map
        else root.find(f"{{{namespace_map['']}}}NumIssues")
    )

    if name_elem is None or name_elem.text is None:
        raise CBLParseError("CBL file missing required 'Name' element")

    name = name_elem.text
    num_issues = int(num_issues_elem.text) if num_issues_elem is not None else 0

    # Extract books
    books_elem = (
        root.find("Books") if not namespace_map else root.find(f"{{{namespace_map['']}}}Books")
    )

    if books_elem is None:
        raise CBLParseError("CBL file missing required 'Books' element")

    books = []
    book_elements = (
        books_elem.findall("Book")
        if not namespace_map
        else books_elem.findall(f"{{{namespace_map['']}}}Book")
    )

    for order, book_elem in enumerate(book_elements, start=1):
        series = book_elem.get("Series", "")
        number = book_elem.get("Number", "")
        volume = book_elem.get("Volume", "")
        year = book_elem.get("Year", "")

        # Find database element
        database_elem = (
            book_elem.find("Database")
            if not namespace_map
            else book_elem.find(f"{{{namespace_map['']}}}Database")
        )

        if database_elem is not None:
            database_name = database_elem.get("Name", "").lower()
            database_series_id = database_elem.get("Series", "")
            database_issue_id = database_elem.get("Issue", "")

            books.append(
                CBLBook(
                    series=series,
                    number=number,
                    volume=volume,
                    year=year,
                    database_name=database_name,
                    database_series_id=database_series_id,
                    database_issue_id=database_issue_id,
                    order=order,
                )
            )

    return CBLData(name=name, num_issues=num_issues, books=books)


@dataclass
class ImportResult:
    """Result of importing a CBL file."""

    reading_list: ReadingList
    issues_added: int
    issues_not_found: list[CBLBook]
    issues_skipped: list[tuple[CBLBook, str]]  # (book, reason)


def import_cbl_file(
    file_path: str | Path,
    user,
    is_private: bool = False,
    attribution_source: str = "",
    attribution_url: str = "",
) -> ImportResult:
    """Import a Comic Book List (.cbl) file into a user's reading list.

    Args:
        file_path: Path to the .cbl file to import
        user: The user who will own the reading list
        is_private: Whether the reading list should be private (default: False)
        attribution_source: Source attribution for the reading list (default: "")
        attribution_url: URL attribution for the reading list (default: "")

    Returns:
        ImportResult object containing the created reading list and import statistics

    Raises:
        CBLParseError: If the file cannot be parsed
        CBLImportError: If the reading list cannot be created
        FileNotFoundError: If the file does not exist
    """
    # Parse the CBL file
    cbl_data = parse_cbl_file(file_path)

    # Check if a reading list with the same name already exists for this user
    existing_list = ReadingList.objects.filter(user=user, name=cbl_data.name).first()
    if existing_list:
        raise CBLImportError(
            f"A reading list named '{cbl_data.name}' already exists for this user. "
            "Please delete the existing list or rename it before importing."
        )

    issues_added = 0
    issues_not_found = []
    issues_skipped = []

    try:
        with transaction.atomic():
            # Create the reading list
            reading_list = ReadingList.objects.create(
                user=user,
                name=cbl_data.name,
                is_private=is_private,
                attribution_source=attribution_source,
                attribution_url=attribution_url,
            )

            # Process each book
            for book in cbl_data.books:
                issue = None

                # Try to find the issue based on the database ID
                if book.database_name == "cv" and book.database_issue_id:
                    # ComicVine ID
                    try:
                        cv_id = int(book.database_issue_id)
                        issue = Issue.objects.filter(cv_id=cv_id).first()
                    except (ValueError, TypeError):
                        issues_skipped.append(
                            (book, f"Invalid ComicVine ID: '{book.database_issue_id}'")
                        )
                        LOGGER.warning(
                            "Invalid ComicVine ID '%s' for %s #%s",
                            book.database_issue_id,
                            book.series,
                            book.number,
                        )
                        continue

                elif book.database_name == "metron" and book.database_issue_id:
                    # Metron ID (primary key)
                    try:
                        metron_id = int(book.database_issue_id)
                        issue = Issue.objects.filter(id=metron_id).first()
                    except (ValueError, TypeError):
                        issues_skipped.append(
                            (book, f"Invalid Metron ID: '{book.database_issue_id}'")
                        )
                        LOGGER.warning(
                            "Invalid Metron ID '%s' for %s #%s",
                            book.database_issue_id,
                            book.series,
                            book.number,
                        )
                        continue

                else:
                    # Unsupported database or missing ID
                    issues_skipped.append(
                        (book, f"Unsupported database '{book.database_name}' or missing issue ID")
                    )
                    continue

                if issue:
                    # Check if this issue is already in the reading list
                    existing = ReadingListItem.objects.filter(
                        reading_list=reading_list, issue=issue
                    ).exists()

                    if existing:
                        # Skip duplicate issue
                        issues_skipped.append((book, "Issue already in reading list"))
                        LOGGER.warning(
                            "Skipping duplicate issue %s in reading list '%s'",
                            issue,
                            reading_list.name,
                        )
                    else:
                        # Add the issue to the reading list
                        ReadingListItem.objects.create(
                            reading_list=reading_list,
                            issue=issue,
                            order=book.order,
                        )
                        issues_added += 1
                        LOGGER.info(
                            "Added issue %s to reading list '%s' at position %s",
                            issue,
                            reading_list.name,
                            book.order,
                        )
                else:
                    # Issue not found in database
                    issues_not_found.append(book)
                    LOGGER.warning(
                        "Issue not found in database: %s #%s (%s ID: %s)",
                        book.series,
                        book.number,
                        book.database_name,
                        book.database_issue_id,
                    )

            LOGGER.info(
                "Import completed: %s issues added, %s not found, %s skipped",
                issues_added,
                len(issues_not_found),
                len(issues_skipped),
            )

    except Exception as e:
        raise CBLImportError(f"Failed to import CBL file: {e}") from e

    return ImportResult(
        reading_list=reading_list,
        issues_added=issues_added,
        issues_not_found=issues_not_found,
        issues_skipped=issues_skipped,
    )

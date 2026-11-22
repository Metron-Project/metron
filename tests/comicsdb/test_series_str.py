"""Tests for the series-type-dependent Series and Issue string formats."""

import pytest

from comicsdb.models.series import SeriesType


@pytest.mark.parametrize(
    ("type_id", "name"),
    [
        (SeriesType.HARDCOVER, "Hardcover"),
        (SeriesType.GRAPHIC_NOVEL, "Graphic Novel"),
        (SeriesType.TRADE_PAPERBACK, "Trade Paperback"),
        (SeriesType.DIGITAL_CHAPTERS, "Digital Chapters"),
        (SeriesType.OMNIBUS, "Omnibus"),
    ],
)
def test_series_type_constants_match_fixture(db, type_id, name):
    assert SeriesType.objects.get(pk=type_id).name == name


@pytest.mark.parametrize(
    ("type_id", "expected"),
    [
        (SeriesType.DIGITAL_CHAPTERS, "Final Crisis (1939) Digital"),
        (SeriesType.TRADE_PAPERBACK, "Final Crisis TPB (1939)"),
        (SeriesType.HARDCOVER, "Final Crisis HC (1939)"),
        (SeriesType.GRAPHIC_NOVEL, "Final Crisis GN (1939)"),
        (None, "Final Crisis (1939)"),  # any other type, e.g. single issue
    ],
)
def test_series_str_by_type(fc_series, single_issue_type, type_id, expected):
    fc_series.series_type_id = type_id or single_issue_type.pk
    assert str(fc_series) == expected


def test_issue_str_for_digital_chapters(basic_issue):
    basic_issue.series.series_type_id = SeriesType.DIGITAL_CHAPTERS
    assert str(basic_issue) == "Final Crisis (1939) Digital Chapter #1"


def test_issue_str_default(basic_issue):
    assert str(basic_issue) == "Final Crisis (1939) #1"

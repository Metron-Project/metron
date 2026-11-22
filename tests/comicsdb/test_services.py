"""Tests for comicsdb.services: which issue tools apply, and the reprint-sync type check."""

import pytest
from django.contrib import messages

from comicsdb.models.series import SeriesType
from comicsdb.services import (
    reprint_sync_blocker,
    supports_credit_duplication,
    supports_reprint_sync,
)

COLLECTED = [SeriesType.TRADE_PAPERBACK, SeriesType.OMNIBUS, SeriesType.HARDCOVER]
NOT_COLLECTED = [SeriesType.GRAPHIC_NOVEL, SeriesType.DIGITAL_CHAPTERS]


@pytest.fixture
def image_issue(basic_issue):
    """basic_issue, moved to a publisher whose credits may be duplicated."""
    publisher = basic_issue.series.publisher
    publisher.name = "Image"
    publisher.save()
    return basic_issue


@pytest.mark.parametrize("type_id", COLLECTED)
def test_collected_editions_support_reprint_sync_only(image_issue, type_id):
    image_issue.series.series_type_id = type_id
    assert supports_reprint_sync(image_issue)
    assert not supports_credit_duplication(image_issue)


@pytest.mark.parametrize("type_id", NOT_COLLECTED)
def test_other_types_support_credit_duplication_only(image_issue, type_id):
    image_issue.series.series_type_id = type_id
    assert not supports_reprint_sync(image_issue)
    assert supports_credit_duplication(image_issue)


@pytest.mark.parametrize("publisher", ["DC Comics", "Marvel"])
def test_excluded_publishers_dont_support_credit_duplication(basic_issue, publisher):
    basic_issue.series.publisher.name = publisher
    assert not supports_credit_duplication(basic_issue)


def test_reprint_sync_blocker_lists_types_by_name(basic_issue):
    level, message = reprint_sync_blocker(basic_issue)
    assert level == messages.ERROR
    assert "Trade Paperback, Omnibus and Hardcover" in message
    assert basic_issue.series.series_type.name in message

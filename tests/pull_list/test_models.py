"""Tests for pull_list models."""

import pytest
from django.db import IntegrityError

from pull_list.models import PullList, PullListSeries


def test_pull_list_str(pull_list, pull_list_user):
    assert str(pull_list) == f"{pull_list_user.username}'s Pull List"


def test_pull_list_series_str(pull_list_with_series, pull_list_series):
    pls = pull_list_with_series.pull_list_series.first()
    assert str(pull_list_series) in str(pls)
    assert str(pull_list_with_series) in str(pls)


def test_pull_list_one_per_user(pull_list_user, pull_list):
    with pytest.raises(IntegrityError):
        PullList.objects.create(user=pull_list_user)


def test_pull_list_series_unique_together(pull_list_with_series, pull_list_series):
    with pytest.raises(IntegrityError):
        PullListSeries.objects.create(pull_list=pull_list_with_series, series=pull_list_series)


def test_pull_list_series_signal_updates_modified(pull_list_with_series, pull_list_series_2):
    original_modified = PullList.objects.get(pk=pull_list_with_series.pk).modified
    PullListSeries.objects.create(pull_list=pull_list_with_series, series=pull_list_series_2)
    updated_modified = PullList.objects.get(pk=pull_list_with_series.pk).modified
    assert updated_modified >= original_modified


def test_pull_list_series_delete_signal_updates_modified(pull_list_with_series):
    original_modified = PullList.objects.get(pk=pull_list_with_series.pk).modified
    pull_list_with_series.pull_list_series.first().delete()
    updated_modified = PullList.objects.get(pk=pull_list_with_series.pk).modified
    assert updated_modified >= original_modified


def test_pull_list_get_absolute_url(pull_list):
    url = pull_list.get_absolute_url()
    assert "/pull-list/" in url

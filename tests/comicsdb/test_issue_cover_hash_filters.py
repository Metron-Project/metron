"""The issue API's cover_hash_near filter finds main covers by perceptual hash similarity."""

import pytest
from django.urls import reverse
from django.utils import timezone

from comicsdb.models import Issue

QUERY_HASH = "c585eb18bf1e5423"
ONE_BIT_OFF = "c585eb18bf1e5422"
FOUR_BITS_OFF = "c585eb18bf1e542c"
TWELVE_BITS_OFF = "c585eb18bf1eabdc"  # last three nibbles complemented
TWENTY_BITS_OFF = "c585eb18bf11abdc"  # last five nibbles complemented
FAR_AWAY = "3a7a14e740e1abdc"  # bitwise complement: 64 bits off


@pytest.fixture
def make_issue(create_user, fc_series):
    user = create_user()

    def make(number, cover_hash, series=None):
        issue = Issue.objects.create(
            series=series or fc_series,
            number=number,
            cover_date=timezone.now().date(),
            edited_by=user,
            created_by=user,
        )
        # pre_save_cover_hash clears cover_hash on issues without an image, so bypass save().
        Issue.objects.filter(pk=issue.pk).update(cover_hash=cover_hash)
        return issue.pk

    return make


@pytest.fixture
def search(api_client_with_credentials):
    def get(**params):
        return api_client_with_credentials.get(reverse("api:issue-list"), params)

    def ids(**params):
        response = get(**params)
        assert response.status_code == 200
        data = response.json()
        result = [row["id"] for row in data["results"]]
        assert data["count"] == len(result)
        return result

    ids.get = get
    return ids


def test_exact_hash_matches(search, make_issue):
    pk = make_issue("1", QUERY_HASH)
    assert search(cover_hash_near=QUERY_HASH) == [pk]


def test_results_are_ordered_closest_first(search, make_issue):
    four = make_issue("1", FOUR_BITS_OFF)
    exact = make_issue("2", QUERY_HASH)
    one = make_issue("3", ONE_BIT_OFF)
    assert search(cover_hash_near=QUERY_HASH) == [exact, one, four]


def test_max_distance_excludes_farther_covers(search, make_issue):
    exact = make_issue("1", QUERY_HASH)
    one = make_issue("2", ONE_BIT_OFF)
    make_issue("3", FOUR_BITS_OFF)
    assert search(cover_hash_near=QUERY_HASH, cover_hash_max_distance=1) == [exact, one]
    assert search(cover_hash_near=QUERY_HASH, cover_hash_max_distance=0) == [exact]


def test_default_max_distance_is_sixteen(search, make_issue):
    four = make_issue("1", FOUR_BITS_OFF)
    twelve = make_issue("2", TWELVE_BITS_OFF)
    make_issue("3", TWENTY_BITS_OFF)
    make_issue("4", FAR_AWAY)
    assert search(cover_hash_near=QUERY_HASH) == [four, twelve]


def test_max_distance_can_be_raised_to_twenty_four(search, make_issue):
    twenty = make_issue("1", TWENTY_BITS_OFF)
    make_issue("2", FAR_AWAY)
    assert search(cover_hash_near=QUERY_HASH, cover_hash_max_distance=24) == [twenty]


def test_issues_without_cover_hash_are_excluded(search, make_issue):
    make_issue("1", "")
    assert search(cover_hash_near="0000000000000000", cover_hash_max_distance=24) == []


def test_uppercase_query_matches(search, make_issue):
    pk = make_issue("1", QUERY_HASH)
    assert search(cover_hash_near=QUERY_HASH.upper()) == [pk]


def test_max_distance_alone_does_not_filter(search, make_issue):
    near = make_issue("1", QUERY_HASH)
    far = make_issue("2", FAR_AWAY)
    assert sorted(search(cover_hash_max_distance=0)) == sorted([near, far])


def test_combines_with_other_filters(search, make_issue, bat_sups_series):
    make_issue("1", QUERY_HASH)
    other = make_issue("1", ONE_BIT_OFF, series=bat_sups_series)
    assert search(cover_hash_near=QUERY_HASH, series_id=bat_sups_series.pk) == [other]


@pytest.mark.parametrize(
    "params",
    [
        {"cover_hash_near": "c585eb18bf1e542"},  # too short
        {"cover_hash_near": "c585eb18bf1e54233"},  # too long
        {"cover_hash_near": "g585eb18bf1e5423"},  # not hex
        {"cover_hash_near": QUERY_HASH, "cover_hash_max_distance": -1},
        {"cover_hash_near": QUERY_HASH, "cover_hash_max_distance": 25},
        {"cover_hash_near": QUERY_HASH, "cover_hash_max_distance": 2.5},
    ],
)
def test_invalid_input_is_rejected(search, params):
    assert search.get(**params).status_code == 400

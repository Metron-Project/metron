"""The issue API's cover_hash_near filter finds main covers by perceptual hash similarity."""

import pytest
from django.urls import reverse
from django.utils import timezone

from comicsdb.models import Credits, Issue, Variant

QUERY_HASH = "c585eb18bf1e5423"
ONE_BIT_OFF = "c585eb18bf1e5422"
FOUR_BITS_OFF = "c585eb18bf1e542c"
EIGHT_BITS_OFF = "c585eb18bf1e54dc"  # last two nibbles complemented
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


def test_default_max_distance_is_ten(search, make_issue):
    four = make_issue("1", FOUR_BITS_OFF)
    eight = make_issue("2", EIGHT_BITS_OFF)
    make_issue("3", TWELVE_BITS_OFF)
    make_issue("4", TWENTY_BITS_OFF)
    make_issue("5", FAR_AWAY)
    assert search(cover_hash_near=QUERY_HASH) == [four, eight]


def test_max_distance_can_be_raised_to_twenty_four(search, make_issue):
    twenty = make_issue("1", TWENTY_BITS_OFF)
    make_issue("2", FAR_AWAY)
    assert search(cover_hash_near=QUERY_HASH, cover_hash_max_distance=24) == [twenty]


def test_issues_without_cover_hash_are_excluded(search, make_issue):
    make_issue("1", "")
    assert search(cover_hash_near="0000000000000000", cover_hash_max_distance=24) == []


@pytest.mark.parametrize("bad_hash", ["c585eb18bf1e542", "c585eb18bf1e542z", " c585eb18bf1e542"])
def test_malformed_stored_hashes_are_skipped(search, make_issue, bad_hash):
    make_issue("1", bad_hash)
    good = make_issue("2", QUERY_HASH)
    assert search(cover_hash_near=QUERY_HASH, cover_hash_max_distance=24) == [good]


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


# These filters join to-many relations and add DISTINCT, which interacts with the distance
# ordering; each case must return every match once, still closest first.


def test_combines_with_upc_filter_matching_main_and_variants(search, make_issue):
    upc = "76194134182900111"
    exact = make_issue("1", QUERY_HASH)
    four = make_issue("2", FOUR_BITS_OFF)
    make_issue("3", ONE_BIT_OFF)  # near, but no matching UPC
    Issue.objects.filter(pk__in=[exact, four]).update(upc=upc)
    for name in ("B", "C"):
        Variant.objects.create(issue_id=exact, name=name, upc=upc)
    assert search(cover_hash_near=QUERY_HASH, upc=upc) == [exact, four]


def test_combines_with_creator_and_role_filters(
    search, make_issue, john_byrne, walter_simonson, writer
):
    exact = make_issue("1", QUERY_HASH)
    four = make_issue("2", FOUR_BITS_OFF)
    make_issue("3", ONE_BIT_OFF)  # near, but uncredited
    # Two writers on one issue would duplicate it without DISTINCT on the role join.
    for issue_id, creator in ((four, john_byrne), (exact, john_byrne), (exact, walter_simonson)):
        Credits.objects.create(issue_id=issue_id, creator=creator).role.add(writer)
    assert search(cover_hash_near=QUERY_HASH, role_id=writer.pk) == [exact, four]
    assert search(cover_hash_near=QUERY_HASH, creator_id=john_byrne.pk) == [exact, four]
    assert search(cover_hash_near=QUERY_HASH, creator_id=john_byrne.pk, role_id=writer.pk) == [
        exact,
        four,
    ]


@pytest.mark.parametrize(
    "params",
    [
        {"cover_hash_near": "c585eb18bf1e542"},  # too short
        {"cover_hash_near": "c585eb18bf1e54233"},  # too long
        {"cover_hash_near": "g585eb18bf1e5423"},  # not hex
        {"cover_hash_near": QUERY_HASH, "cover_hash_max_distance": -1},
        {"cover_hash_near": QUERY_HASH, "cover_hash_max_distance": 25},
        {"cover_hash_near": QUERY_HASH, "cover_hash_max_distance": 2.5},
        {"cover_hash_max_distance": 25},  # still validated without cover_hash_near
    ],
)
def test_invalid_input_is_rejected(search, params):
    assert search.get(**params).status_code == 400

"""CoverHashDistance computes the Hamming distance between hex phash strings in PostgreSQL."""

import pytest
from django.db.models import F, Value

from comicsdb.filters.issue import CoverHashDistance
from comicsdb.models import Issue

STORED_HASH = "c585eb18bf1e5423"


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        (STORED_HASH, 0),
        ("c585eb18bf1e5422", 1),  # last nibble 3 -> 2 flips one bit
        ("c585eb18bf1e542c", 4),  # last nibble 3 -> c flips four bits
        ("3a7a14e740e1abdc", 64),  # bitwise complement
    ],
)
def test_cover_hash_distance(basic_issue, query, expected):
    # pre_save_cover_hash clears cover_hash on issues without an image, so bypass save().
    Issue.objects.filter(pk=basic_issue.pk).update(cover_hash=STORED_HASH)
    distance = (
        Issue.objects.filter(pk=basic_issue.pk)
        .annotate(distance=CoverHashDistance(F("cover_hash"), Value(query)))
        .values_list("distance", flat=True)
        .get()
    )
    assert distance == expected

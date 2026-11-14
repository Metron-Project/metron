"""CoverHashDistance computes the Hamming distance between 64-bit phashes in PostgreSQL."""

import pytest
from django.db.models import F, Value

from comicsdb.filters.issue import CoverHashDistance
from comicsdb.models import Issue
from comicsdb.models.issue import HexToBigint

STORED_HASH = "c585eb18bf1e5423"


def set_cover_hash(issue, cover_hash):
    # pre_save_cover_hash clears cover_hash on issues without an image, so bypass save().
    Issue.objects.filter(pk=issue.pk).update(cover_hash=cover_hash)


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
    set_cover_hash(basic_issue, STORED_HASH)
    target = HexToBigint(Value(query))
    distance = (
        Issue.objects.filter(pk=basic_issue.pk)
        .annotate(distance=CoverHashDistance(F("cover_hash_bits"), target))
        .values_list("distance", flat=True)
        .get()
    )
    assert distance == expected


@pytest.mark.parametrize(
    ("cover_hash", "expected"),
    [
        (STORED_HASH, -4213703384817052637),  # high bit set: stored as a negative bigint
        ("C585EB18BF1E5423", -4213703384817052637),  # uppercase hex
        ("3a7a14e740e1abdc", 4213703384817052636),
    ],
)
def test_cover_hash_bits_is_signed_64_bit_value(basic_issue, cover_hash, expected):
    set_cover_hash(basic_issue, cover_hash)
    basic_issue.refresh_from_db()
    assert basic_issue.cover_hash_bits == expected


@pytest.mark.parametrize("cover_hash", ["", "c585eb18bf1e542", "c585eb18bf1e542z"])
def test_cover_hash_bits_is_null_for_blank_or_malformed_hash(basic_issue, cover_hash):
    set_cover_hash(basic_issue, cover_hash)
    basic_issue.refresh_from_db()
    assert basic_issue.cover_hash_bits is None

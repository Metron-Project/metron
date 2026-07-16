from datetime import timedelta

import pytest
from django.utils import timezone

from users.models import SUPPORTER_TIERS, CustomUser, OpenCollectiveDonation, tier_for_amount


def test_user_creation(create_user):
    user = create_user()
    assert isinstance(user, CustomUser)
    assert str(user) == user.username


@pytest.mark.django_db
@pytest.mark.parametrize(("username", "email"), [("", "foo@bar.com"), ("Foo", "")])
def test_user_creation_missing_info(username, email, test_password):
    with pytest.raises(ValueError):  # noqa: PT011
        assert CustomUser.objects.create_user(
            username=username, email=email, password=test_password
        )


@pytest.mark.django_db
def test_superuser_creation(test_password, test_email):
    obj = CustomUser.objects.create_superuser(
        username="Foo", password=test_password, email=test_email
    )
    assert isinstance(obj, CustomUser)
    assert obj.is_superuser is True
    assert obj.is_staff is True


@pytest.mark.django_db
@pytest.mark.parametrize(("superuser", "staff"), [(True, False), (False, True)])
def test_superuser_creation_without_roles(superuser, staff, test_password, test_email):
    with pytest.raises(ValueError):  # noqa: PT011
        assert CustomUser.objects.create_superuser(
            username="Foo",
            password=test_password,
            email=test_email,
            is_superuser=superuser,
            is_staff=staff,
        )


def test_is_supporter_false_when_unset(create_user):
    user = create_user()
    assert user.supporter_until is None
    assert user.is_supporter is False


def test_is_supporter_true_when_in_future(create_user):
    user = create_user()
    user.supporter_until = timezone.now() + timedelta(days=1)
    assert user.is_supporter is True


def test_is_supporter_false_when_expired(create_user):
    user = create_user()
    user.supporter_until = timezone.now() - timedelta(days=1)
    assert user.is_supporter is False


@pytest.mark.django_db
def test_opencollective_donation_str(create_user):
    user = create_user()
    donation = OpenCollectiveDonation.objects.create(
        transaction_id="12345",
        user=user,
        email=user.email,
        amount=500,
        donated_at=timezone.now(),
    )
    assert str(donation) == f"{user.email} - 12345"


@pytest.mark.django_db
def test_opencollective_donation_user_set_null_on_delete(create_user):
    user = create_user()
    donation = OpenCollectiveDonation.objects.create(
        transaction_id="12345",
        user=user,
        email=user.email,
        amount=500,
        donated_at=timezone.now(),
    )
    user.delete()
    donation.refresh_from_db()
    assert donation.user is None


@pytest.mark.parametrize(
    ("cents", "expected_slug"),
    [
        (0, None),
        (199, None),  # one cent below Friend
        (200, "friend"),  # exact Friend threshold
        (300, "friend"),  # $3 -> Friend (round down)
        (499, "friend"),  # one cent below Backer
        (500, "backer"),  # exact Backer threshold
        (700, "backer"),  # $7 -> Backer (round down)
        (999, "backer"),  # one cent below Sponsor
        (1000, "sponsor"),  # exact Sponsor threshold
        (1200, "sponsor"),  # $12 -> Sponsor (round down)
        (2499, "sponsor"),  # one cent below Mega Sponsor
        (2500, "mega_sponsor"),  # exact Mega Sponsor threshold
        (3000, "mega_sponsor"),  # $30 -> Mega Sponsor
        (100000, "mega_sponsor"),  # well above ceiling - flat, not scaling
    ],
)
def test_tier_for_amount(cents, expected_slug):
    assert tier_for_amount(cents) == expected_slug


def test_supporter_daily_limit_and_display_none_when_not_supporter(create_user):
    user = create_user()
    user.supporter_tier = "backer"
    assert user.is_supporter is False
    assert user.supporter_daily_limit is None
    assert user.supporter_tier_display is None


@pytest.mark.parametrize(
    ("slug", "expected_limit", "expected_display"),
    [
        ("friend", 7500, "Friend"),
        ("backer", 10000, "Backer"),
        ("sponsor", 15000, "Sponsor"),
        ("mega_sponsor", 25000, "Mega Sponsor"),
    ],
)
def test_supporter_daily_limit_and_display_by_tier(
    create_user, slug, expected_limit, expected_display
):
    user = create_user()
    user.supporter_until = timezone.now() + timedelta(days=1)
    user.supporter_tier = slug
    assert user.supporter_daily_limit == expected_limit
    assert user.supporter_tier_display == expected_display


def test_supporter_daily_limit_falls_back_to_lowest_tier_when_blank(create_user):
    """Data-integrity fallback: is_supporter True but supporter_tier blank (e.g. a
    row set before tiers existed)."""
    user = create_user()
    user.supporter_until = timezone.now() + timedelta(days=1)
    assert user.supporter_tier == ""
    assert user.supporter_daily_limit == SUPPORTER_TIERS[-1][3]
    assert user.supporter_tier_display == SUPPORTER_TIERS[-1][2]

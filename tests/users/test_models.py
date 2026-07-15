from datetime import timedelta

import pytest
from django.utils import timezone

from users.models import CustomUser, OpenCollectiveDonation


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

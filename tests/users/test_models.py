import pytest

from users.models import CustomUser


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

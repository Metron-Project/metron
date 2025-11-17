# ruff: noqa: PLC0415
"""Shared fixtures for all tests."""

import uuid

import pytest
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command

from comicsdb.models import Credits, Imprint, Universe
from comicsdb.models.arc import Arc
from comicsdb.models.character import Character
from comicsdb.models.creator import Creator
from comicsdb.models.issue import Issue
from comicsdb.models.publisher import Publisher
from comicsdb.models.series import Series, SeriesType
from comicsdb.models.team import Team
from users.models import CustomUser

NUMBER_OF_ISSUES = 35


@pytest.fixture
def test_password():
    return "strong-test-pass"


@pytest.fixture
def test_email():
    return "foo@bar.com"


@pytest.fixture
def create_user(db, test_password, test_email):
    def make_user(**kwargs):
        kwargs["password"] = test_password
        kwargs["email"] = test_email
        if "username" not in kwargs:
            kwargs["username"] = str(uuid.uuid4())
        return CustomUser.objects.create_user(**kwargs)

    return make_user


@pytest.fixture
def create_editor_group(db):
    group, _ = Group.objects.get_or_create(name="editors")
    models = [
        Arc,
        Character,
        Creator,
        Credits,
        Imprint,
        Issue,
        Publisher,
        Series,
        Team,
        Universe,
    ]
    for model in models:
        ct = ContentType.objects.get_for_model(model)
        perms = Permission.objects.filter(content_type=ct)
        for perm in perms:
            if "add" in perm.codename:
                group.permissions.add(perm)
            if "change" in perm.codename:
                group.permissions.add(perm)
    return group


@pytest.fixture
def create_staff_user(create_user, create_editor_group):
    user: CustomUser = create_user()
    user.is_staff = True
    user.groups.add(create_editor_group)
    user.save()
    return user


@pytest.fixture
def auto_login_user(db, client, create_user, test_password):
    def make_auto_login(user=None):
        if user is None:
            user = create_user()
        client.login(username=user.username, password=test_password)
        return client, user

    return make_auto_login


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def api_client_with_credentials(db, create_user, api_client):
    user = create_user()
    api_client.force_authenticate(user=user)
    yield api_client
    api_client.force_authenticate(user=None)


@pytest.fixture
def api_client_with_staff_credentials(db, create_staff_user, api_client):
    api_client.force_authenticate(user=create_staff_user)
    yield api_client
    api_client.force_authenticate(user=None)


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        from django.db import connection

        call_command("loaddata", "../../comicsdb/fixtures/series_type.yaml")
        # Create system user with id=1 if it doesn't exist
        if not CustomUser.objects.filter(id=1).exists():
            user = CustomUser(
                id=1,
                username="system",
                email="system@metron.com",
                is_active=True,
            )
            user.set_password("system")
            user.save()

            # Reset the sequence to start from 2 so other users don't conflict
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT setval(pg_get_serial_sequence('users_customuser', 'id'), 2, false);"
                )


@pytest.fixture
def single_issue_type(db):
    return SeriesType.objects.get(name__icontains="single")


@pytest.fixture
def trade_paperback_type(db):
    return SeriesType.objects.get(name="Trade Paperback")


@pytest.fixture
def omnibus_type(db):
    return SeriesType.objects.get(name="Omnibus")


@pytest.fixture
def hardcover_type(db):
    return SeriesType.objects.get(name="Hardcover")

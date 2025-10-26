"""Tests for django-simple-history integration."""

from django.contrib.auth import get_user_model

from comicsdb.models import (
    Arc,
    Character,
    Creator,
    Genre,
    Imprint,
    Issue,
    Publisher,
    Series,
    Team,
    Universe,
)

User = get_user_model()


# Basic History Creation Tests


def test_publisher_history_created_on_save(create_user):
    """Test that a historical record is created when a Publisher is saved."""
    user = create_user()
    publisher = Publisher.objects.create(
        name="Test Publisher",
        slug="test-publisher",
        created_by=user,
        edited_by=user,
    )

    assert publisher.history.count() == 1
    history_record = publisher.history.first()
    assert history_record.name == "Test Publisher"
    assert history_record.history_type == "+"  # Created


def test_creator_history_created_on_save(create_user):
    """Test that a historical record is created when a Creator is saved."""
    user = create_user()
    creator = Creator.objects.create(
        name="John Doe",
        slug="john-doe",
        created_by=user,
        edited_by=user,
    )

    assert creator.history.count() == 1
    history_record = creator.history.first()
    assert history_record.name == "John Doe"
    assert history_record.history_type == "+"


def test_arc_history_created_on_save(create_user):
    """Test that a historical record is created when an Arc is saved."""
    user = create_user()
    arc = Arc.objects.create(
        name="Test Arc",
        slug="test-arc",
        created_by=user,
        edited_by=user,
    )

    assert arc.history.count() == 1
    history_record = arc.history.first()
    assert history_record.name == "Test Arc"
    assert history_record.history_type == "+"


def test_universe_history_created_on_save(create_user, dc_comics):
    """Test that a historical record is created when a Universe is saved."""
    user = create_user()
    universe = Universe.objects.create(
        name="Test Universe",
        slug="test-universe",
        publisher=dc_comics,
        created_by=user,
        edited_by=user,
    )

    assert universe.history.count() == 1
    history_record = universe.history.first()
    assert history_record.name == "Test Universe"
    assert history_record.history_type == "+"


def test_genre_history_created_on_save(db):
    """Test that a historical record is created when a Genre is saved."""
    genre = Genre.objects.create(name="Science Fiction")

    assert genre.history.count() == 1
    history_record = genre.history.first()
    assert history_record.name == "Science Fiction"
    assert history_record.history_type == "+"


def test_imprint_history_created_on_save(create_user, dc_comics):
    """Test that a historical record is created when an Imprint is saved."""
    user = create_user()
    imprint = Imprint.objects.create(
        name="Test Imprint",
        slug="test-imprint",
        publisher=dc_comics,
        created_by=user,
        edited_by=user,
    )

    assert imprint.history.count() == 1
    history_record = imprint.history.first()
    assert history_record.name == "Test Imprint"
    assert history_record.history_type == "+"


# Field Change Tracking Tests


def test_publisher_name_change_tracked(create_user):
    """Test that changing a Publisher name creates a new historical record."""
    user = create_user()
    publisher = Publisher.objects.create(
        name="Original Name",
        slug="original-name",
        created_by=user,
        edited_by=user,
    )

    # Change the name
    publisher.name = "Updated Name"
    publisher.save()

    assert publisher.history.count() == 2
    latest_history = publisher.history.first()
    assert latest_history.name == "Updated Name"
    assert latest_history.history_type == "~"  # Modified

    oldest_history = publisher.history.last()
    assert oldest_history.name == "Original Name"
    assert oldest_history.history_type == "+"


def test_creator_description_change_tracked(create_user):
    """Test that changing a Creator description creates a new historical record."""
    user = create_user()
    creator = Creator.objects.create(
        name="Jane Doe",
        slug="jane-doe",
        desc="Original description",
        created_by=user,
        edited_by=user,
    )

    creator.desc = "Updated description"
    creator.save()

    assert creator.history.count() == 2
    latest_history = creator.history.first()
    assert latest_history.desc == "Updated description"
    assert latest_history.history_type == "~"


def test_multiple_field_changes_tracked(create_user):
    """Test that multiple field changes are tracked in a single update."""
    user = create_user()
    publisher = Publisher.objects.create(
        name="Test Publisher",
        slug="test-publisher",
        desc="Original",
        created_by=user,
        edited_by=user,
    )

    publisher.name = "New Name"
    publisher.desc = "New Description"
    publisher.save()

    assert publisher.history.count() == 2
    latest_history = publisher.history.first()
    assert latest_history.name == "New Name"
    assert latest_history.desc == "New Description"


def test_multiple_sequential_changes_tracked(create_user):
    """Test that multiple sequential changes create separate history records."""
    user = create_user()
    arc = Arc.objects.create(
        name="Version 1",
        slug="version-1",
        created_by=user,
        edited_by=user,
    )

    arc.name = "Version 2"
    arc.save()

    arc.name = "Version 3"
    arc.save()

    arc.name = "Version 4"
    arc.save()

    assert arc.history.count() == 4

    # Verify the history in reverse chronological order
    history_records = list(arc.history.all())
    assert history_records[0].name == "Version 4"
    assert history_records[1].name == "Version 3"
    assert history_records[2].name == "Version 2"
    assert history_records[3].name == "Version 1"


# M2M History Tracking Tests


def test_character_creators_m2m_tracked(create_user, john_byrne, walter_simonson):
    """Test that adding creators to a Character is tracked in history."""
    user = create_user()
    character = Character.objects.create(
        name="Test Hero",
        slug="test-hero",
        created_by=user,
        edited_by=user,
    )

    # Add creators
    character.creators.add(john_byrne)
    assert character.history.count() == 2  # Create + M2M change

    character.creators.add(walter_simonson)
    assert character.history.count() == 3  # Previous + new M2M change


def test_character_teams_m2m_tracked(create_user, teen_titans, avengers):
    """Test that adding teams to a Character is tracked in history."""
    user = create_user()
    character = Character.objects.create(
        name="Test Hero",
        slug="test-hero",
        created_by=user,
        edited_by=user,
    )

    character.teams.add(teen_titans)
    assert character.history.count() == 2

    character.teams.add(avengers)
    assert character.history.count() == 3


def test_character_universes_m2m_tracked(create_user, earth_2_universe):
    """Test that adding universes to a Character is tracked in history."""
    user = create_user()
    character = Character.objects.create(
        name="Test Hero",
        slug="test-hero",
        created_by=user,
        edited_by=user,
    )

    character.universes.add(earth_2_universe)
    assert character.history.count() == 2


def test_team_creators_m2m_tracked(create_user, john_byrne):
    """Test that adding creators to a Team is tracked in history."""
    user = create_user()
    team = Team.objects.create(
        name="Test Team",
        slug="test-team",
        created_by=user,
        edited_by=user,
    )

    team.creators.add(john_byrne)
    assert team.history.count() == 2


def test_series_genres_m2m_tracked(create_user, dc_comics, single_issue_type):
    """Test that adding genres to a Series is tracked in history."""
    user = create_user()
    genre = Genre.objects.create(name="Action")

    series = Series.objects.create(
        name="Test Series",
        slug="test-series",
        sort_name="Test Series",
        volume=1,
        year_began=2024,
        series_type=single_issue_type,
        publisher=dc_comics,
        created_by=user,
        edited_by=user,
    )

    series.genres.add(genre)
    assert series.history.count() == 2


def test_issue_arcs_m2m_tracked(create_user, fc_series, fc_arc):
    """Test that adding arcs to an Issue is tracked in history."""
    user = create_user()
    issue = Issue.objects.create(
        series=fc_series,
        number="1",
        slug=f"{fc_series.slug}-1",
        cover_date="2024-01-01",
        created_by=user,
        edited_by=user,
    )

    issue.arcs.add(fc_arc)
    assert issue.history.count() == 2


def test_issue_characters_m2m_tracked(create_user, fc_series, superman):
    """Test that adding characters to an Issue is tracked in history."""
    user = create_user()
    issue = Issue.objects.create(
        series=fc_series,
        number="1",
        slug=f"{fc_series.slug}-1",
        cover_date="2024-01-01",
        created_by=user,
        edited_by=user,
    )

    issue.characters.add(superman)
    assert issue.history.count() == 2


def test_m2m_removal_tracked(create_user, john_byrne):
    """Test that removing M2M relationships is tracked in history."""
    user = create_user()
    character = Character.objects.create(
        name="Test Hero",
        slug="test-hero",
        created_by=user,
        edited_by=user,
    )

    character.creators.add(john_byrne)
    initial_count = character.history.count()

    character.creators.remove(john_byrne)
    assert character.history.count() == initial_count + 1


# User Attribution Tests


def test_history_user_tracked(create_user):
    """Test that the user who made changes is tracked in history."""
    user1 = create_user()
    user2 = create_user()

    publisher = Publisher.objects.create(
        name="Test Publisher",
        slug="test-publisher",
        created_by=user1,
        edited_by=user1,
    )

    # Change made by user2
    publisher.name = "Updated Publisher"
    publisher.edited_by = user2
    publisher.save()

    assert publisher.history.count() == 2

    latest_history = publisher.history.first()
    assert latest_history.edited_by == user2

    oldest_history = publisher.history.last()
    assert oldest_history.created_by == user1


def test_different_users_create_separate_history(create_user):
    """Test that changes by different users create separate history records."""
    user1 = create_user()
    user2 = create_user()
    user3 = create_user()

    arc = Arc.objects.create(
        name="Test Arc",
        slug="test-arc",
        created_by=user1,
        edited_by=user1,
    )

    arc.desc = "Updated by user 2"
    arc.edited_by = user2
    arc.save()

    arc.desc = "Updated by user 3"
    arc.edited_by = user3
    arc.save()

    assert arc.history.count() == 3

    history_records = list(arc.history.all())
    assert history_records[0].edited_by == user3
    assert history_records[1].edited_by == user2
    assert history_records[2].created_by == user1


# History Deletion Tests


def test_publisher_deletion_tracked(create_user):
    """Test that deleting a Publisher creates a deletion history record."""
    user = create_user()
    publisher = Publisher.objects.create(
        name="To Be Deleted",
        slug="to-be-deleted",
        created_by=user,
        edited_by=user,
    )

    publisher_id = publisher.id
    publisher.delete()

    # History should still exist after deletion
    from comicsdb.models.publisher import HistoricalPublisher

    deletion_record = HistoricalPublisher.objects.filter(id=publisher_id).first()
    assert deletion_record is not None
    assert deletion_record.history_type == "-"  # Deleted


def test_creator_deletion_tracked(create_user):
    """Test that deleting a Creator creates a deletion history record."""
    user = create_user()
    creator = Creator.objects.create(
        name="To Be Deleted",
        slug="to-be-deleted",
        created_by=user,
        edited_by=user,
    )

    creator_id = creator.id
    creator.delete()

    from comicsdb.models.creator import HistoricalCreator

    deletion_record = HistoricalCreator.objects.filter(id=creator_id).first()
    assert deletion_record is not None
    assert deletion_record.history_type == "-"


# History Retrieval Tests


def test_as_of_date_retrieval(create_user):
    """Test retrieving an object's state as of a specific date."""
    user = create_user()
    publisher = Publisher.objects.create(
        name="Version 1",
        slug="version-1",
        created_by=user,
        edited_by=user,
    )

    # Get the timestamp after first save
    first_save_time = publisher.history.first().history_date

    # Make changes
    publisher.name = "Version 2"
    publisher.save()

    publisher.name = "Version 3"
    publisher.save()

    # Retrieve the state as of the first save
    historical_instance = publisher.history.as_of(first_save_time)
    assert historical_instance.name == "Version 1"


def test_filter_by_history_type(create_user):
    """Test filtering historical records by history type."""
    user = create_user()
    arc = Arc.objects.create(
        name="Test Arc",
        slug="test-arc",
        created_by=user,
        edited_by=user,
    )

    arc.name = "Updated Arc"
    arc.save()

    # Filter for creation records
    created_records = arc.history.filter(history_type="+")
    assert created_records.count() == 1

    # Filter for modification records
    modified_records = arc.history.filter(history_type="~")
    assert modified_records.count() == 1


def test_get_previous_version(create_user):
    """Test getting the previous version of an object."""
    user = create_user()
    creator = Creator.objects.create(
        name="Version 1",
        slug="version-1",
        created_by=user,
        edited_by=user,
    )

    creator.name = "Version 2"
    creator.save()

    creator.name = "Version 3"
    creator.save()

    # Get the most recent history record
    current_history = creator.history.first()

    # Get the previous record
    previous_history = current_history.prev_record
    assert previous_history is not None
    assert previous_history.name == "Version 2"

    # Get the one before that
    initial_history = previous_history.prev_record
    assert initial_history is not None
    assert initial_history.name == "Version 1"


def test_get_next_version(create_user, dc_comics):
    """Test getting the next version of an object."""
    user = create_user()
    universe = Universe.objects.create(
        name="Version 1",
        slug="version-1",
        publisher=dc_comics,
        created_by=user,
        edited_by=user,
    )

    universe.name = "Version 2"
    universe.save()

    universe.name = "Version 3"
    universe.save()

    # Get the oldest history record
    oldest_history = universe.history.last()

    # Get the next record
    next_history = oldest_history.next_record
    assert next_history is not None
    assert next_history.name == "Version 2"


# Edge Case Tests


def test_no_change_still_creates_history(create_user):
    """Test that saving without changes still creates a history record."""
    user = create_user()
    publisher = Publisher.objects.create(
        name="Test Publisher",
        slug="test-publisher",
        created_by=user,
        edited_by=user,
    )

    initial_count = publisher.history.count()

    # Save without making changes
    publisher.save()

    # History count should increase
    assert publisher.history.count() == initial_count + 1


def test_null_description_tracked(create_user):
    """Test that null/empty descriptions are properly tracked."""
    user = create_user()
    arc = Arc.objects.create(
        name="Test Arc",
        slug="test-arc",
        desc="",
        created_by=user,
        edited_by=user,
    )

    history = arc.history.first()
    assert history.desc == ""

    arc.desc = "Now has description"
    arc.save()

    latest_history = arc.history.first()
    assert latest_history.desc == "Now has description"


def test_empty_m2m_set_tracked(create_user):
    """Test that creating objects with no M2M relationships is tracked."""
    user = create_user()
    character = Character.objects.create(
        name="Solo Character",
        slug="solo-character",
        created_by=user,
        edited_by=user,
    )

    assert character.history.count() == 1
    assert character.creators.count() == 0
    assert character.teams.count() == 0
    assert character.universes.count() == 0


def test_bulk_m2m_addition(create_user, john_byrne, walter_simonson):
    """Test that bulk M2M additions are tracked."""
    user = create_user()
    character = Character.objects.create(
        name="Test Character",
        slug="test-character",
        created_by=user,
        edited_by=user,
    )

    # Add multiple creators at once
    character.creators.set([john_byrne, walter_simonson])

    # Should create history for the M2M change
    assert character.history.count() == 2

from datetime import timedelta
from unittest.mock import MagicMock

from django.utils import timezone

from comicsdb.models import Arc, Character, Issue, Series, Team
from comicsdb.signals import (
    update_related_modified,
    update_series_modified_on_issue_delete,
    update_series_modified_on_issue_save,
)


def test_issue_save_updates_series_modified_on_create(basic_issue):
    past = timezone.now() - timedelta(days=1)
    Series.objects.filter(pk=basic_issue.series_id).update(modified=past)
    basic_issue.series.refresh_from_db()
    old_modified = basic_issue.series.modified

    update_series_modified_on_issue_save(sender=Issue, instance=basic_issue, created=True)
    basic_issue.series.refresh_from_db()
    assert basic_issue.series.modified > old_modified


def test_issue_save_does_not_update_series_on_update(basic_issue):
    past = timezone.now() - timedelta(days=1)
    Series.objects.filter(pk=basic_issue.series_id).update(modified=past)
    basic_issue.series.refresh_from_db()
    old_modified = basic_issue.series.modified

    update_series_modified_on_issue_save(sender=Issue, instance=basic_issue, created=False)
    basic_issue.series.refresh_from_db()
    assert basic_issue.series.modified == old_modified


def test_issue_delete_updates_series_modified(basic_issue):
    past = timezone.now() - timedelta(days=1)
    Series.objects.filter(pk=basic_issue.series_id).update(modified=past)
    basic_issue.series.refresh_from_db()
    old_modified = basic_issue.series.modified

    update_series_modified_on_issue_delete(sender=Issue, instance=basic_issue)
    basic_issue.series.refresh_from_db()
    assert basic_issue.series.modified > old_modified


def test_update_related_modified_ignores_non_add_remove_actions(wwh_arc):
    past = timezone.now() - timedelta(days=1)
    Arc.objects.filter(pk=wwh_arc.pk).update(modified=past)
    wwh_arc.refresh_from_db()
    old_modified = wwh_arc.modified

    update_related_modified(Arc, MagicMock(spec=Issue), "pre_add", {wwh_arc.pk})
    wwh_arc.refresh_from_db()
    assert wwh_arc.modified == old_modified


def test_update_related_modified_post_add_from_issue(wwh_arc):
    past = timezone.now() - timedelta(days=1)
    Arc.objects.filter(pk=wwh_arc.pk).update(modified=past)
    wwh_arc.refresh_from_db()
    old_modified = wwh_arc.modified

    update_related_modified(Arc, MagicMock(spec=Issue), "post_add", {wwh_arc.pk})
    wwh_arc.refresh_from_db()
    assert wwh_arc.modified > old_modified


def test_update_related_modified_post_remove_from_issue(superman):
    past = timezone.now() - timedelta(days=1)
    Character.objects.filter(pk=superman.pk).update(modified=past)
    superman.refresh_from_db()
    old_modified = superman.modified

    update_related_modified(Character, MagicMock(spec=Issue), "post_remove", {superman.pk})
    superman.refresh_from_db()
    assert superman.modified > old_modified


def test_update_related_modified_from_parent_side(wwh_arc):
    past = timezone.now() - timedelta(days=1)
    Arc.objects.filter(pk=wwh_arc.pk).update(modified=past)
    wwh_arc.refresh_from_db()
    old_modified = wwh_arc.modified

    update_related_modified(Arc, wwh_arc, "post_add", None)
    wwh_arc.refresh_from_db()
    assert wwh_arc.modified > old_modified


def test_update_related_modified_empty_pk_set_from_issue(wwh_arc):
    past = timezone.now() - timedelta(days=1)
    Arc.objects.filter(pk=wwh_arc.pk).update(modified=past)
    wwh_arc.refresh_from_db()
    old_modified = wwh_arc.modified

    update_related_modified(Arc, MagicMock(spec=Issue), "post_add", set())
    wwh_arc.refresh_from_db()
    assert wwh_arc.modified == old_modified


def test_arc_m2m_signal_updates_arc_modified(basic_issue, wwh_arc):
    past = timezone.now() - timedelta(days=1)
    Arc.objects.filter(pk=wwh_arc.pk).update(modified=past)
    wwh_arc.refresh_from_db()
    old_modified = wwh_arc.modified

    basic_issue.arcs.add(wwh_arc)
    wwh_arc.refresh_from_db()
    assert wwh_arc.modified > old_modified


def test_character_m2m_signal_updates_character_modified(basic_issue, superman):
    past = timezone.now() - timedelta(days=1)
    Character.objects.filter(pk=superman.pk).update(modified=past)
    superman.refresh_from_db()
    old_modified = superman.modified

    basic_issue.characters.add(superman)
    superman.refresh_from_db()
    assert superman.modified > old_modified


def test_team_m2m_signal_updates_team_modified(basic_issue, teen_titans):
    past = timezone.now() - timedelta(days=1)
    Team.objects.filter(pk=teen_titans.pk).update(modified=past)
    teen_titans.refresh_from_db()
    old_modified = teen_titans.modified

    basic_issue.teams.add(teen_titans)
    teen_titans.refresh_from_db()
    assert teen_titans.modified > old_modified


def test_m2m_remove_updates_modified(basic_issue, wwh_arc):
    basic_issue.arcs.add(wwh_arc)

    past = timezone.now() - timedelta(days=1)
    Arc.objects.filter(pk=wwh_arc.pk).update(modified=past)
    wwh_arc.refresh_from_db()
    old_modified = wwh_arc.modified

    basic_issue.arcs.remove(wwh_arc)
    wwh_arc.refresh_from_db()
    assert wwh_arc.modified > old_modified


def test_creating_issue_updates_series_modified(create_user, fc_series):
    past = timezone.now() - timedelta(days=1)
    Series.objects.filter(pk=fc_series.pk).update(modified=past)
    fc_series.refresh_from_db()
    old_modified = fc_series.modified

    user = create_user()
    Issue.objects.create(
        series=fc_series,
        number="99",
        slug="final-crisis-99",
        cover_date=timezone.now().date(),
        edited_by=user,
        created_by=user,
    )
    fc_series.refresh_from_db()
    assert fc_series.modified > old_modified


def test_deleting_issue_updates_series_modified(basic_issue):
    series = basic_issue.series
    past = timezone.now() - timedelta(days=1)
    Series.objects.filter(pk=series.pk).update(modified=past)
    series.refresh_from_db()
    old_modified = series.modified

    basic_issue.delete()
    series.refresh_from_db()
    assert series.modified > old_modified

from functools import partial

from django.apps import AppConfig
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_delete, pre_save

from api.cache import ModelLabel
from comicsdb.signals import (
    bump_cache,
    bump_cache_on_name_change,
    bump_owner_modified_on_m2m_change,
    pre_delete_credit,
    pre_delete_image,
    track_name_change,
    update_issue_modified_on_credit_change,
    update_issue_modified_on_credit_role_change,
    update_issue_modified_on_reprint_change,
    update_issue_modified_on_universe_change,
    update_issue_modified_on_variant_change,
    update_parent_modified_on_attribution_delete,
    update_parent_modified_on_attribution_save,
    update_related_modified_on_m2m_change,
    update_series_modified_on_associated_change,
    update_series_modified_on_issue_change,
)


class ComicsdbConfig(AppConfig):
    name = "comicsdb"
    verbose_name = "Comics DB"

    def ready(self):
        arc = self.get_model("Arc")
        character = self.get_model("Character")
        creator = self.get_model("Creator")
        imprint = self.get_model("Imprint")
        issue = self.get_model("Issue")
        publisher = self.get_model("Publisher")
        series = self.get_model("Series")
        team = self.get_model("Team")
        universe = self.get_model("Universe")
        variant = self.get_model("Variant")
        attribution = self.get_model("Attribution")
        credits_ = self.get_model("Credits")

        # Note on weak=False below: receivers built with `partial` have no other
        # strong reference, so Django's default weak-reference receiver storage
        # would let them be garbage-collected right after connecting, silently
        # dropping the connection.

        # Delete the stored image (and its thumbnails) along with the object.
        for model in (arc, character, creator, issue, publisher, team, variant):
            pre_delete.connect(
                pre_delete_image, sender=model, dispatch_uid=f"pre_delete_{model._meta.model_name}"
            )

        # Issue.arcs/characters/teams: bump `modified` on both sides plus the
        # parent's cache version (see update_related_modified_on_m2m_change).
        issue_parent_m2m = (
            ("arcs", arc, ModelLabel.ARC),
            ("characters", character, ModelLabel.CHARACTER),
            ("teams", team, ModelLabel.TEAM),
        )
        for field_name, parent_model, label in issue_parent_m2m:
            m2m_changed.connect(
                partial(update_related_modified_on_m2m_change, parent_model, label),
                sender=getattr(issue, field_name).through,
                weak=False,
                dispatch_uid=f"m2m_changed_issue_{parent_model._meta.model_name}_modified",
            )

        # Plain m2m fields whose relation is embedded only in the owner's own
        # responses: bump the owner's `modified` and cache version (see
        # bump_owner_modified_on_m2m_change).
        owner_m2m = (
            (character, "creators", ModelLabel.CHARACTER),
            (character, "teams", ModelLabel.CHARACTER),
            (character, "universes", ModelLabel.CHARACTER),
            (series, "genres", ModelLabel.SERIES),
            (team, "creators", ModelLabel.TEAM),
            (team, "universes", ModelLabel.TEAM),
        )
        for owner_model, field_name, label in owner_m2m:
            field = owner_model._meta.get_field(field_name)
            m2m_changed.connect(
                partial(bump_owner_modified_on_m2m_change, owner_model, label),
                sender=field.remote_field.through,
                weak=False,
                dispatch_uid=(
                    f"m2m_changed_{owner_model._meta.model_name}_"
                    f"{field.related_model._meta.model_name}_modified"
                ),
            )

        # Handlers with relation-specific behavior.
        post_save.connect(
            update_series_modified_on_issue_change,
            sender=issue,
            dispatch_uid="post_save_issue_series_modified",
        )
        post_delete.connect(
            update_series_modified_on_issue_change,
            sender=issue,
            dispatch_uid="post_delete_issue_series_modified",
        )
        m2m_changed.connect(
            update_issue_modified_on_universe_change,
            sender=issue.universes.through,
            dispatch_uid="m2m_changed_issue_universe_modified",
        )
        m2m_changed.connect(
            update_issue_modified_on_reprint_change,
            sender=issue.reprints.through,
            dispatch_uid="m2m_changed_issue_reprint_modified",
        )
        m2m_changed.connect(
            update_series_modified_on_associated_change,
            sender=series.associated.through,
            dispatch_uid="m2m_changed_series_associated_modified",
        )
        post_save.connect(
            update_issue_modified_on_variant_change,
            sender=variant,
            dispatch_uid="post_save_variant_issue_modified",
        )
        post_delete.connect(
            update_issue_modified_on_variant_change,
            sender=variant,
            dispatch_uid="post_delete_variant_issue_modified",
        )
        post_save.connect(
            update_parent_modified_on_attribution_save,
            sender=attribution,
            dispatch_uid="post_save_attribution_parent_modified",
        )
        post_delete.connect(
            update_parent_modified_on_attribution_delete,
            sender=attribution,
            dispatch_uid="post_delete_attribution_parent_modified",
        )
        pre_delete.connect(pre_delete_credit, sender=credits_, dispatch_uid="pre_delete_credits")
        post_save.connect(
            update_issue_modified_on_credit_change,
            sender=credits_,
            dispatch_uid="post_save_credit_issue_modified",
        )
        post_delete.connect(
            update_issue_modified_on_credit_change,
            sender=credits_,
            dispatch_uid="post_delete_credit_issue_modified",
        )
        m2m_changed.connect(
            update_issue_modified_on_credit_role_change,
            sender=credits_.role.through,
            dispatch_uid="m2m_changed_credit_role_modified",
        )

        # Models whose cache invalidation is *only* "bump my own version
        # counter" on every save/delete -- see bump_cache() in
        # comicsdb/signals.py. Everything above this point wires up
        # handlers with model-specific behavior (image cleanup, modified
        # cascades); this is the uniform remainder.
        cache_bump_models = (
            (arc, ModelLabel.ARC),
            (character, ModelLabel.CHARACTER),
            (creator, ModelLabel.CREATOR),
            (imprint, ModelLabel.IMPRINT),
            (publisher, ModelLabel.PUBLISHER),
            (series, ModelLabel.SERIES),
            (team, ModelLabel.TEAM),
            (universe, ModelLabel.UNIVERSE),
        )
        for model, label in cache_bump_models:
            bumper = partial(bump_cache, label)
            post_save.connect(
                bumper, sender=model, weak=False, dispatch_uid=f"post_save_{label}_cache"
            )
            post_delete.connect(
                bumper, sender=model, weak=False, dispatch_uid=f"post_delete_{label}_cache"
            )

        # Name-only counters (see ModelLabel.PUBLISHER_NAME): bumped on save
        # only when `name` changed, and always on delete (e.g. deleting an
        # Imprint SET_NULLs Series.imprint without touching Series.modified).
        name_bump_models = (
            (imprint, ModelLabel.IMPRINT_NAME),
            (publisher, ModelLabel.PUBLISHER_NAME),
        )
        for model, label in name_bump_models:
            pre_save.connect(
                track_name_change, sender=model, dispatch_uid=f"pre_save_{label}_track"
            )
            post_save.connect(
                partial(bump_cache_on_name_change, label),
                sender=model,
                weak=False,
                dispatch_uid=f"post_save_{label}_cache",
            )
            post_delete.connect(
                partial(bump_cache, label),
                sender=model,
                weak=False,
                dispatch_uid=f"post_delete_{label}_cache",
            )

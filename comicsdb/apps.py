from functools import partial

from django.apps import AppConfig
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_delete

from api.cache import ModelLabel
from comicsdb.signals import (
    bump_cache,
    pre_delete_credit,
    pre_delete_image,
    update_arc_modified,
    update_character_modified,
    update_issue_modified_on_credit_change,
    update_issue_modified_on_credit_role_change,
    update_issue_modified_on_reprint_change,
    update_issue_modified_on_universe_change,
    update_issue_modified_on_variant_change,
    update_series_modified_on_issue_delete,
    update_series_modified_on_issue_save,
    update_team_modified,
)


class ComicsdbConfig(AppConfig):
    name = "comicsdb"
    verbose_name = "Comics DB"

    def ready(self):
        arc = self.get_model("Arc")
        pre_delete.connect(pre_delete_image, sender=arc, dispatch_uid="pre_delete_arc")

        character = self.get_model("Character")
        pre_delete.connect(pre_delete_image, sender=character, dispatch_uid="pre_delete_character")

        creator = self.get_model("Creator")
        pre_delete.connect(pre_delete_image, sender=creator, dispatch_uid="pre_delete_creator")

        issue = self.get_model("Issue")
        pre_delete.connect(pre_delete_image, sender=issue, dispatch_uid="pre_delete_issue")
        post_save.connect(
            update_series_modified_on_issue_save,
            sender=issue,
            dispatch_uid="post_save_issue_series_modified",
        )
        post_delete.connect(
            update_series_modified_on_issue_delete,
            sender=issue,
            dispatch_uid="post_delete_issue_series_modified",
        )
        m2m_changed.connect(
            update_arc_modified,
            sender=issue.arcs.through,
            dispatch_uid="m2m_changed_issue_arc_modified",
        )
        m2m_changed.connect(
            update_character_modified,
            sender=issue.characters.through,
            dispatch_uid="m2m_changed_issue_character_modified",
        )
        m2m_changed.connect(
            update_team_modified,
            sender=issue.teams.through,
            dispatch_uid="m2m_changed_issue_team_modified",
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

        imprint = self.get_model("Imprint")

        publisher = self.get_model("Publisher")
        pre_delete.connect(pre_delete_image, sender=publisher, dispatch_uid="pre_delete_publisher")

        series = self.get_model("Series")

        team = self.get_model("Team")
        pre_delete.connect(pre_delete_image, sender=team, dispatch_uid="pre_delete_team")

        universe = self.get_model("Universe")

        variant = self.get_model("Variant")
        pre_delete.connect(pre_delete_image, sender=variant, dispatch_uid="pre_delete_variant")
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

        credits_ = self.get_model("Credits")
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
            # weak=False: `bumper` is a local `partial` with no other
            # strong reference, so Django's default weak-reference
            # receiver storage would let it be garbage-collected right
            # after this loop iteration ends, silently dropping the
            # connection.
            post_save.connect(
                bumper, sender=model, weak=False, dispatch_uid=f"post_save_{label}_cache"
            )
            post_delete.connect(
                bumper, sender=model, weak=False, dispatch_uid=f"post_delete_{label}_cache"
            )

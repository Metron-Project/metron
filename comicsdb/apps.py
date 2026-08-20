from django.apps import AppConfig
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_delete

from comicsdb.signals import (
    bump_arc_cache,
    bump_character_cache,
    bump_creator_cache,
    bump_imprint_cache,
    bump_publisher_cache,
    bump_series_cache,
    bump_team_cache,
    bump_universe_cache,
    pre_delete_credit,
    pre_delete_image,
    update_arc_modified,
    update_character_modified,
    update_issue_modified_on_credit_change,
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
        post_save.connect(bump_arc_cache, sender=arc, dispatch_uid="post_save_arc_cache")
        post_delete.connect(bump_arc_cache, sender=arc, dispatch_uid="post_delete_arc_cache")

        character = self.get_model("Character")
        pre_delete.connect(pre_delete_image, sender=character, dispatch_uid="pre_delete_character")
        post_save.connect(
            bump_character_cache, sender=character, dispatch_uid="post_save_character_cache"
        )
        post_delete.connect(
            bump_character_cache, sender=character, dispatch_uid="post_delete_character_cache"
        )

        creator = self.get_model("Creator")
        pre_delete.connect(pre_delete_image, sender=creator, dispatch_uid="pre_delete_creator")
        post_save.connect(
            bump_creator_cache, sender=creator, dispatch_uid="post_save_creator_cache"
        )
        post_delete.connect(
            bump_creator_cache, sender=creator, dispatch_uid="post_delete_creator_cache"
        )

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

        imprint = self.get_model("Imprint")
        post_save.connect(
            bump_imprint_cache, sender=imprint, dispatch_uid="post_save_imprint_cache"
        )
        post_delete.connect(
            bump_imprint_cache, sender=imprint, dispatch_uid="post_delete_imprint_cache"
        )

        publisher = self.get_model("Publisher")
        pre_delete.connect(pre_delete_image, sender=publisher, dispatch_uid="pre_delete_publisher")
        post_save.connect(
            bump_publisher_cache, sender=publisher, dispatch_uid="post_save_publisher_cache"
        )
        post_delete.connect(
            bump_publisher_cache, sender=publisher, dispatch_uid="post_delete_publisher_cache"
        )

        series = self.get_model("Series")
        post_save.connect(bump_series_cache, sender=series, dispatch_uid="post_save_series_cache")
        post_delete.connect(
            bump_series_cache, sender=series, dispatch_uid="post_delete_series_cache"
        )

        team = self.get_model("Team")
        pre_delete.connect(pre_delete_image, sender=team, dispatch_uid="pre_delete_team")
        post_save.connect(bump_team_cache, sender=team, dispatch_uid="post_save_team_cache")
        post_delete.connect(bump_team_cache, sender=team, dispatch_uid="post_delete_team_cache")

        universe = self.get_model("Universe")
        post_save.connect(
            bump_universe_cache, sender=universe, dispatch_uid="post_save_universe_cache"
        )
        post_delete.connect(
            bump_universe_cache, sender=universe, dispatch_uid="post_delete_universe_cache"
        )

        variant = self.get_model("Variant")
        pre_delete.connect(pre_delete_image, sender=variant, dispatch_uid="pre_delete_variant")

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

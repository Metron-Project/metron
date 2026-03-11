from django.apps import AppConfig
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_delete

from comicsdb.signals import (
    pre_delete_credit,
    pre_delete_image,
    update_arc_modified,
    update_character_modified,
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

        publisher = self.get_model("Publisher")
        pre_delete.connect(pre_delete_image, sender=publisher, dispatch_uid="pre_delete_publisher")

        team = self.get_model("Team")
        pre_delete.connect(pre_delete_image, sender=team, dispatch_uid="pre_delete_team")

        variant = self.get_model("Variant")
        pre_delete.connect(pre_delete_image, sender=variant, dispatch_uid="pre_delete_variant")

        credits_ = self.get_model("Credits")
        pre_delete.connect(pre_delete_credit, sender=credits_, dispatch_uid="pre_delete_credits")

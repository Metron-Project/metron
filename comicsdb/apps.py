from django.apps import AppConfig
from django.db.models.signals import pre_delete, pre_save

from comicsdb.signals import (
    pre_delete_image,
    pre_save_series_slug,
    pre_save_slug_from_name,
)


class ComicsdbConfig(AppConfig):
    name = "comicsdb"
    verbose_name = "Comics DB"

    def ready(self):
        arc = self.get_model("Arc")
        pre_delete.connect(pre_delete_image, sender=arc, dispatch_uid="pre_delete_arc")
        pre_save.connect(
            pre_save_slug_from_name, sender=arc, dispatch_uid="pre_save_arc"
        )

        character = self.get_model("Character")
        pre_delete.connect(
            pre_delete_image, sender=character, dispatch_uid="pre_delete_character"
        )
        pre_save.connect(
            pre_save_slug_from_name, sender=character, dispatch_uid="pre_save_character"
        )

        creator = self.get_model("Creator")
        pre_delete.connect(
            pre_delete_image, sender=creator, dispatch_uid="pre_delete_creator"
        )
        pre_save.connect(
            pre_save_slug_from_name, sender=creator, dispatch_uid="pre_save_creator"
        )

        issue = self.get_model("Issue")
        pre_delete.connect(
            pre_delete_image, sender=issue, dispatch_uid="pre_delete_issue"
        )

        publisher = self.get_model("Publisher")
        pre_delete.connect(
            pre_delete_image, sender=publisher, dispatch_uid="pre_delete_publisher"
        )
        pre_save.connect(
            pre_save_slug_from_name, sender=publisher, dispatch_uid="pre_save_publisher"
        )

        series = self.get_model("Series")
        pre_save.connect(
            pre_save_series_slug, sender=series, dispatch_uid="pre_save_series"
        )

        team = self.get_model("Team")
        pre_delete.connect(
            pre_delete_image, sender=team, dispatch_uid="pre_delete_team"
        )
        pre_save.connect(
            pre_save_slug_from_name, sender=team, dispatch_uid="pre_save_team"
        )

        variant = self.get_model("Variant")
        pre_delete.connect(
            pre_delete_image, sender=variant, dispatch_uid="pre_delete_variant"
        )

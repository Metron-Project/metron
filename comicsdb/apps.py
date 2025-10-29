from django.apps import AppConfig
from django.db.models.signals import pre_delete

from comicsdb.signals import pre_delete_credit, pre_delete_image


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

        publisher = self.get_model("Publisher")
        pre_delete.connect(pre_delete_image, sender=publisher, dispatch_uid="pre_delete_publisher")

        team = self.get_model("Team")
        pre_delete.connect(pre_delete_image, sender=team, dispatch_uid="pre_delete_team")

        variant = self.get_model("Variant")
        pre_delete.connect(pre_delete_image, sender=variant, dispatch_uid="pre_delete_variant")

        credits_ = self.get_model("Credits")
        pre_delete.connect(pre_delete_credit, sender=credits_, dispatch_uid="pre_delete_credits")

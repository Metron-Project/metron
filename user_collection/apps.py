from django.apps import AppConfig
from django.db.models.signals import post_save

from user_collection.signals import sync_issue_rating_from_collection_item


class UserCollectionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "user_collection"

    def ready(self):
        collection_item = self.get_model("CollectionItem")
        post_save.connect(
            sync_issue_rating_from_collection_item,
            sender=collection_item,
            dispatch_uid="post_save_sync_issue_rating_from_collection_item",
        )

from django.apps import AppConfig
from django.db.models.signals import post_delete, post_save

from reading_lists.signals import update_reading_list_modified_on_item_change


class ReadingListsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "reading_lists"

    def ready(self):
        reading_list_item = self.get_model("ReadingListItem")
        post_save.connect(
            update_reading_list_modified_on_item_change,
            sender=reading_list_item,
            dispatch_uid="post_save_reading_list_item_modified",
        )
        post_delete.connect(
            update_reading_list_modified_on_item_change,
            sender=reading_list_item,
            dispatch_uid="post_delete_reading_list_item_modified",
        )

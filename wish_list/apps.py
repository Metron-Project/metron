from django.apps import AppConfig
from django.db.models.signals import post_delete, post_save

from wish_list.signals import update_wish_list_modified_on_item_change


class WishListConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "wish_list"

    def ready(self):
        wish_list_item = self.get_model("WishListItem")
        post_save.connect(
            update_wish_list_modified_on_item_change,
            sender=wish_list_item,
            dispatch_uid="post_save_wish_list_item_modified",
        )
        post_delete.connect(
            update_wish_list_modified_on_item_change,
            sender=wish_list_item,
            dispatch_uid="post_delete_wish_list_item_modified",
        )

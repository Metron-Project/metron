from django.apps import AppConfig
from django.db.models.signals import post_delete, post_save

from pull_list.signals import update_pull_list_modified_on_series_change


class PullListConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "pull_list"

    def ready(self):
        pull_list_series = self.get_model("PullListSeries")
        post_save.connect(
            update_pull_list_modified_on_series_change,
            sender=pull_list_series,
            dispatch_uid="post_save_pull_list_series_modified",
        )
        post_delete.connect(
            update_pull_list_modified_on_series_change,
            sender=pull_list_series,
            dispatch_uid="post_delete_pull_list_series_modified",
        )

from django.apps import AppConfig


class ReadingListsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "reading_lists"

    def ready(self):
        """Import autocomplete views when the app is ready."""
        import reading_lists.autocomplete  # noqa: F401 PLC0415

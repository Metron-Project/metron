from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = "users"

    def ready(self):
        from django.contrib.auth.signals import user_logged_in

        from users.signals import log_user_login

        user_logged_in.connect(log_user_login)

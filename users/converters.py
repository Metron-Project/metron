RESERVED_USERNAMES = {
    "login",
    "logout",
    "password",
    "password_change",
    "password_change_done",
    "password_reset",
    "password_reset_done",
    "password_reset_confirm",
    "password_reset_complete",
    "signup",
    "update",
    "activate",
    "account_activation_sent",
}


class UsernameConverter:
    """Custom path converter that matches usernames but excludes reserved routes."""

    regex = r"[^/]+"

    def to_python(self, value):
        if value.lower() in RESERVED_USERNAMES:
            raise ValueError("Reserved username")
        return value

    def to_url(self, value):
        return value

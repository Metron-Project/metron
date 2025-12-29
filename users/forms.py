import logging
from typing import Any

from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.forms import ClearableFileInput, EmailField, EmailInput

from users.models import CustomUser
from users.utils import check_email_domain

LOGGER = logging.getLogger(__name__)


class CustomUserCreationForm(UserCreationForm):
    email = EmailField(
        max_length=254,
        help_text=(
            "Required. Enter a valid email address. Temporary email addresses are not allowed."
        ),
        required=True,
    )

    def clean(self) -> dict[str, Any]:
        blocklist = {
            "hey.com",
            "inboxes.app",
            "passinbox.com",
            "passmail.net",
            "usemx.de",
            "officialwizard.xyz",
        }  # List of providers that provide temp email addresses.
        whitelist = {"gmail.com", "yahoo.com", "proton.me"}

        email: str = self.cleaned_data.get("email")
        if email is None:
            LOGGER.error("User didn't add an email address")
            raise ValidationError("Email address is not valid.")

        if CustomUser.objects.filter(email=email).exists():
            LOGGER.warning("'%s' already exists", email)
            raise ValidationError("Email already exists")

        try:
            _, domain = email.split("@")
        except ValueError as exc:
            LOGGER.warning("Email: %s | Error: %s", email, exc)
            raise ValidationError("Email address is not valid.") from exc

        if domain in blocklist:
            LOGGER.warning("'%s' is a temporary email address.", email)
            raise ValidationError("Temporary email addresses are not allowed.")

        if domain not in whitelist:
            resp = check_email_domain(email)
            if resp is None:
                raise ValidationError("Error creating account. Contact the site administrator.")
            if resp["block"] is True:
                if resp["disposable"] is True:
                    LOGGER.warning("'%s' is a temporary email address.", email)
                    raise ValidationError("Temporary email addresses are not allowed.")
                LOGGER.warning("'%s' is not a valid email address.", email)
                raise ValidationError("Email address is not valid.")
        return super().clean()

    class Meta(UserCreationForm):
        model = CustomUser
        fields = ("username", "email")


class CustomUserChangeForm(UserChangeForm):
    email = EmailField(
        max_length=254,
        help_text="Required. Enter a valid email address.",
        required=True,
        widget=EmailInput(attrs={"class": "input"}),
        error_messages={"required": "Please provide valid email."},
    )

    class Meta:
        model = CustomUser
        fields = ("username", "first_name", "last_name", "email", "bio", "image")
        widgets = {
            "image": ClearableFileInput(),
        }

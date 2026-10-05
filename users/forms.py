import logging
from typing import Any

from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.forms import (
    CharField,
    ClearableFileInput,
    EmailField,
    EmailInput,
    Form,
    PasswordInput,
)
from django.utils.translation import gettext_lazy as _

from users.models import CustomUser
from users.utils import check_email_domain

LOGGER = logging.getLogger(__name__)

# Providers that hand out temporary email addresses.
EMAIL_DOMAIN_BLOCKLIST = {
    "cloudinbox.top",
    "duck.com",
    "hey.com",
    "inboxes.app",
    "passinbox.com",
    "passmail.net",
    "officialwizard.xyz",
    "simplelogin.com",
    "sixtimesnine.org",
    "usemx.de",
}
# Well-known providers that skip the (paid) domain-check API call.
EMAIL_DOMAIN_ALLOWLIST = {"gmail.com", "yahoo.com", "proton.me"}


def validate_email_allowed(email: str, exclude_pk: int | None = None) -> None:
    """Raise ValidationError unless ``email`` may be used for an account.

    Shared by signup and email changes so a profile edit can't bypass the
    signup checks. ``exclude_pk`` skips the user changing their own address.
    """
    others = CustomUser.objects.filter(email__iexact=email)
    if exclude_pk is not None:
        others = others.exclude(pk=exclude_pk)
    if others.exists():
        LOGGER.warning("'%s' already exists", email)
        raise ValidationError(_("Email already exists"))

    try:
        _unused, domain = email.split("@")
    except ValueError as exc:
        LOGGER.warning("Email: %s | Error: %s", email, exc)
        raise ValidationError(_("Email address is not valid.")) from exc

    if domain in EMAIL_DOMAIN_BLOCKLIST:
        LOGGER.warning("'%s' is a temporary email address.", email)
        raise ValidationError(_("Temporary email addresses are not allowed."))

    if domain not in EMAIL_DOMAIN_ALLOWLIST:
        resp = check_email_domain(email)
        if resp is None:
            raise ValidationError(_("Error creating account. Contact the site administrator."))
        if resp["block"] is True:
            if resp["disposable"] is True:
                LOGGER.warning("'%s' is a temporary email address.", email)
                raise ValidationError(_("Temporary email addresses are not allowed."))
            LOGGER.warning("'%s' is not a valid email address.", email)
            raise ValidationError(_("Email address is not valid."))


class CustomUserCreationForm(UserCreationForm):
    email = EmailField(
        max_length=254,
        help_text=_(
            "Required. Enter a valid email address. Temporary email addresses are not allowed."
        ),
        required=True,
    )

    def clean(self) -> dict[str, Any]:
        email: str = self.cleaned_data.get("email")
        if email is None:
            LOGGER.error("User didn't add an email address")
            raise ValidationError(_("Email address is not valid."))

        validate_email_allowed(email)
        return super().clean()

    class Meta(UserCreationForm):
        model = CustomUser
        fields = ("username", "email")


class CustomUserChangeForm(UserChangeForm):
    email = EmailField(
        max_length=254,
        help_text=_("Required. Enter a valid email address."),
        required=True,
        widget=EmailInput(attrs={"class": "input"}),
        error_messages={"required": _("Please provide valid email.")},
    )

    current_password = CharField(
        label=_("Current password"),
        required=False,
        strip=False,
        widget=PasswordInput(attrs={"autocomplete": "current-password", "class": "input"}),
        help_text=_("Required to change your email address."),
    )

    class Meta:
        model = CustomUser
        fields = ("username", "first_name", "last_name", "email", "bio", "image")
        widgets = {
            "image": ClearableFileInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Captured before validation, which writes the submitted email onto the instance.
        self.original_email = self.instance.email

    @property
    def pending_email(self) -> str | None:
        """The new email address awaiting confirmation, or None if it wasn't changed."""
        email = self.cleaned_data.get("email")
        return email if email and email != self.original_email else None

    def clean_email(self):
        email = self.cleaned_data["email"]
        if email != self.original_email:
            validate_email_allowed(email, exclude_pk=self.instance.pk)
        return email

    def clean(self):
        cleaned_data = super().clean()
        if self.pending_email:
            password = cleaned_data.get("current_password")
            if not password or not self.instance.check_password(password):
                self.add_error(
                    "current_password",
                    _("Enter your current password to change your email address."),
                )
        return cleaned_data

    def save(self, commit=True):
        # A new email address only takes effect once confirmed from that inbox
        # (see users.views.confirm_email_change), so keep the current one for now.
        user = super().save(commit=False)
        user.email = self.original_email
        if commit:
            user.save()
            self._save_m2m()
        return user


class DeleteAccountForm(Form):
    password = CharField(
        label=_("Current password"),
        strip=False,
        widget=PasswordInput(attrs={"autocomplete": "current-password", "class": "input"}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise ValidationError(_("Your password was entered incorrectly."))
        return password

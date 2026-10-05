import logging
import re
import smtplib
import time
from datetime import date

from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.sites.shortcuts import get_current_site
from django.core import signing
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _, gettext_lazy as _lazy
from django.views.generic import DetailView, ListView

# Import models for counting
from comicsdb.models import (
    Arc,
    Character,
    Creator,
    Imprint,
    Issue,
    Publisher,
    Series,
    Team,
    Universe,
)
from comicsdb.views.mixins import SearchMixin
from metron.utils import HCAPTCHA_UNAVAILABLE, get_recaptcha_auth
from user_collection.models import CollectionItem
from users.forms import CustomUserChangeForm, CustomUserCreationForm, DeleteAccountForm
from users.models import ApiToken, CustomUser, SignupSettings
from users.tokens import account_activation_token
from users.utils import send_pushover

logger = logging.getLogger(__name__)

PAGINATE_BY = 28
SUSTAINED_LIMIT = 5000
SUSTAINED_DURATION = 86400  # 1 day in seconds
SIGNUP_IP_LIMIT = 1
SIGNUP_IP_WINDOW = 60 * 60 * 25  # 1 day + an hour of cleanup headroom
EMAIL_CHANGE_SALT = "users.email-change"
EMAIL_CHANGE_MAX_AGE = 60 * 60 * 24 * 3  # 3 days


def _client_ip(request):
    # nginx (nginx/nginx.conf) always overwrites X-Real-IP with its own
    # observed connecting address, so it's safe to trust - unlike
    # X-Forwarded-For, which nginx appends to rather than replaces, so it can
    # carry a client-supplied prefix. Falls back to REMOTE_ADDR for local dev
    # (runserver with no proxy in front, where there's no X-Real-IP header).
    return request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR", "unknown")


def _signup_ip_key(prefix, request):
    return f"{prefix}:ip:{_client_ip(request)}:{date.today().isoformat()}"


def _signup_ip_count(request):
    return cache.get(_signup_ip_key("signup_count", request), 0)


def _record_signup(request, username):
    key = _signup_ip_key("signup_count", request)
    cache.add(key, 0, timeout=SIGNUP_IP_WINDOW)
    cache.incr(key)
    # Only the first signup from this IP/day wins - cache.add is a no-op if
    # a username is already recorded.
    cache.add(_signup_ip_key("signup_first_user", request), username, timeout=SIGNUP_IP_WINDOW)


def _notify_signup_rate_limit_hit(request):
    ip = _client_ip(request)
    count = _signup_ip_count(request)
    first_user = cache.get(_signup_ip_key("signup_first_user", request), "unknown")
    # cache.add only succeeds the first time per IP/day, so repeated blocked
    # retries from the same client don't spam a pushover notice each time.
    notified_key = _signup_ip_key("signup_rate_limit_notified", request)
    if cache.add(notified_key, True, timeout=SIGNUP_IP_WINDOW):
        logger.warning(
            "Signup rate limit hit for IP %s (%d accounts today, first: %s)",
            ip,
            count,
            first_user,
        )
        send_pushover(
            f"Signup rate limit hit for {ip} ({count} accounts created today, first: {first_user})."
        )


def _send_email(request, subject, template_base, context, to):
    """Send ``template_base``.txt with ``template_base``.html as its HTML alternative.

    Adds ``protocol`` and ``domain`` to the context so templates build links with
    the request's scheme (https in production, where SECURE_PROXY_SSL_HEADER is
    set). Raises smtplib.SMTPException/OSError on failure, like EmailMessage.send().
    """
    context = {
        **context,
        "protocol": "https" if request.is_secure() else "http",
        "domain": get_current_site(request).domain,
    }
    email = EmailMultiAlternatives(
        subject=subject,
        body=render_to_string(f"{template_base}.txt", context, request=request),
        to=[to],
    )
    email.attach_alternative(
        render_to_string(f"{template_base}.html", context, request=request), "text/html"
    )
    email.send(using="default")


def is_activated(user, token):
    return user is not None and account_activation_token.check_token(user, token)


def account_activation_sent(request):
    return render(request, "registration/account_activation_sent.html")


# TODO: Remove once the clean activate route has been deployed for 3+ days.
# The activate route used to be a regex passed to path(), which kept the regex text
# literally around the <uidb64>/<token> slots, so emailed links looked like
# activate/(?MTE4OQ[0-9A-Za-z_\-]+)/(?dfz4wj-002cf17a...[0-9A-Za-z]{1,13}-...)/.
# The current route still matches those two segments; this unwraps the real values so
# links sent before the fix work until their tokens expire (PASSWORD_RESET_TIMEOUT).
_LEGACY_ACTIVATION_PART = re.compile(r"^\(\?([0-9A-Za-z_-]+)\[.*\)$")


def _unwrap_legacy_activation_part(value):
    match = _LEGACY_ACTIVATION_PART.match(value)
    return match.group(1) if match else value


def activate(request, uidb64, token):
    uidb64 = _unwrap_legacy_activation_part(uidb64)
    token = _unwrap_legacy_activation_part(token)
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except TypeError, ValueError, OverflowError, CustomUser.DoesNotExist:
        return render(request, "registration/account_activation_invalid.html")

    if not is_activated(user, token):
        return render(request, "registration/account_activation_invalid.html")

    user.is_active = True
    user.email_confirmed = True
    user.save()
    login(request, user)
    # Send pushover notification tha user activated account
    send_pushover(f"{user} activated their account on Metron.")
    ip = _client_ip(request)
    logger.info(
        "User activated their account on Metron (user=%s, ip=%s)",
        user.username,
        ip,
        extra={"username": user.username, "ip": ip},
    )
    # Add a message asking the user to star the repository.
    link = f"<a href='/wiki/editing-guidelines/'>{_('Editing Guidelines')}</a>"
    # Interpolated content is our own translation catalog text, not user input.
    msg = mark_safe(  # noqa: S308
        _(
            "If you are planning on adding new information to the database, please refer "
            "to the %(link)s."
        )
        % {"link": link}
    )
    messages.success(request, msg)

    return redirect("home")


def signup(request):  # sourcery skip: extract-method
    settings_obj = SignupSettings.get_solo()
    if not settings_obj.signups_enabled:
        return render(
            request,
            "registration/signups_disabled.html",
            {"message": settings_obj.disabled_message},
        )

    if request.method == "POST":
        if _signup_ip_count(request) >= SIGNUP_IP_LIMIT:
            _notify_signup_rate_limit_hit(request)
            return render(request, "registration/signup_rate_limited.html", status=429)

        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            result = get_recaptcha_auth(request)

            if HCAPTCHA_UNAVAILABLE in result.get("error-codes", []):
                # An hCaptcha outage, not a failed check: tell the user to retry
                # rather than falling through to "activation email sent".
                form.add_error(
                    None,
                    _(
                        "We were unable to verify the captcha right now. "
                        "Please try again in a few minutes."
                    ),
                )
                return render(request, "registration/signup.html", {"form": form})

            if result["success"]:
                user: CustomUser = form.save(commit=False)
                user.is_active = False
                user.save()
                context = {
                    "user": user,
                    "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                    "token": account_activation_token.make_token(user),
                }
                try:
                    _send_email(
                        request,
                        _("Activate Your Metron Account"),
                        "registration/account_activation_email",
                        context,
                        user.email,
                    )
                except smtplib.SMTPException, OSError:
                    # There's no way to resend the activation email, so don't leave
                    # behind an inactive account holding the username/email, and
                    # don't count it against the IP limit, so the user can retry.
                    logger.exception("Failed to send activation email to %s", user.username)
                    user.delete()
                    form.add_error(
                        None,
                        _(
                            "We were unable to send your activation email. "
                            "Please try again in at a later time."
                        ),
                    )
                    return render(request, "registration/signup.html", {"form": form})
                _record_signup(request, user.username)
                # Let's send a pushover notice that a user requested an account.
                send_pushover(f"{user} signed up for an account on Metron.")
                ip = _client_ip(request)
                logger.info(
                    "User signed up for an account on Metron (user=%s, ip=%s)",
                    user.username,
                    ip,
                    extra={"username": user.username, "ip": ip},
                )

            return redirect("account_activation_sent")
    else:
        form = CustomUserCreationForm()
    return render(request, "registration/signup.html", {"form": form})


class ChangePasswordView(SuccessMessageMixin, PasswordChangeView):
    template_name = "users/change_password.html"
    success_message = _lazy("Successfully Changed Your Password")
    success_url = reverse_lazy("home")


def _email_change_token(user_pk, old_email, new_email):
    # Tied to the current address, so the link stops working once it's used or
    # once another change to the address has been confirmed. Callers pass the
    # stored address explicitly: after form validation the user instance already
    # holds the submitted one.
    return signing.dumps(
        {"user": user_pk, "old_email": old_email, "new_email": new_email},
        salt=EMAIL_CHANGE_SALT,
    )


def change_profile(request):
    if not request.user.is_authenticated:
        return redirect("login")
    if request.method == "POST":
        old_email = request.user.email
        form = CustomUserChangeForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            new_email = form.pending_email
            if new_email:
                token = _email_change_token(request.user.pk, old_email, new_email)
                try:
                    _send_email(
                        request,
                        _("Confirm your new Metron email address"),
                        "registration/email_change_confirm_email",
                        {"user": request.user, "token": token, "new_email": new_email},
                        new_email,
                    )
                except smtplib.SMTPException, OSError:
                    logger.exception("Failed to send email change confirmation")
                    form.add_error(
                        "email",
                        _(
                            "We were unable to send a confirmation email to that address. "
                            "Please try again later."
                        ),
                    )
                    return render(request, "users/change_profile.html", {"form": form})

            user = form.save()
            update_session_auth_hash(request, user)  # Important!

            if new_email:
                # Best effort: let the current address know, in case this wasn't the
                # account owner. The change itself still needs the new inbox to confirm.
                try:
                    _send_email(
                        request,
                        _("Your Metron email address change was requested"),
                        "registration/email_change_notice_email",
                        {"user": user, "new_email": new_email},
                        old_email,
                    )
                except smtplib.SMTPException, OSError:
                    logger.exception("Failed to send email change notice")
                messages.info(
                    request,
                    _(
                        "We've sent a confirmation link to %(email)s. Your email address "
                        "will change once you follow it."
                    )
                    % {"email": new_email},
                )
            messages.success(request, _("Your profile was successfully updated!"))
            return redirect("user-detail", username=request.user.username)
        messages.error(request, _("Please correct the error below."))
    else:
        form = CustomUserChangeForm(instance=request.user)
    return render(request, "users/change_profile.html", {"form": form})


def confirm_email_change(request, token):
    """Apply an email change once the new address has followed its confirmation link."""
    invalid_message = _("This email confirmation link is invalid or has expired.")
    try:
        data = signing.loads(token, salt=EMAIL_CHANGE_SALT, max_age=EMAIL_CHANGE_MAX_AGE)
    except signing.BadSignature:  # Includes SignatureExpired.
        messages.error(request, invalid_message)
        return redirect("home")

    user = CustomUser.objects.filter(pk=data.get("user")).first()
    if user is None or user.email != data.get("old_email"):
        messages.error(request, invalid_message)
        return redirect("home")

    new_email = data["new_email"]
    if CustomUser.objects.filter(email__iexact=new_email).exclude(pk=user.pk).exists():
        messages.error(request, _("That email address is already in use by another account."))
        return redirect("home")

    user.email = new_email
    user.email_confirmed = True
    user.save(update_fields=["email", "email_confirmed"])
    messages.success(request, _("Your email address has been updated."))
    if request.user.is_authenticated and request.user.pk == user.pk:
        return redirect("user-detail", username=user.username)
    return redirect("login")


def delete_account(request):
    if not request.user.is_authenticated:
        return redirect("login")
    if request.method == "POST":
        form = DeleteAccountForm(request.user, request.POST)
        if form.is_valid():
            user = request.user
            logout(request)
            user.delete()
            messages.success(request, _("Your account has been deleted."))
            return redirect("home")
    else:
        form = DeleteAccountForm(request.user)
    return render(request, "users/delete_account.html", {"form": form})


def api_tokens(request):
    if not request.user.is_authenticated:
        return redirect("login")

    new_token = None
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        _instance, new_token = ApiToken.objects.create(user=request.user, name=name)
        messages.success(
            request,
            _("New API token created. Copy it now — you won't be able to see it again."),
        )

    context = {
        "tokens": request.user.auth_token_set.order_by("-created"),
        "new_token": new_token,
    }
    return render(request, "users/api_token.html", context)


def revoke_api_token(request, digest):
    if not request.user.is_authenticated:
        return redirect("login")
    token = get_object_or_404(ApiToken, digest=digest, user=request.user)
    if request.method == "POST":
        token.delete()
        messages.success(request, _("API token revoked."))
    return redirect("api_tokens")


def user_profile_redirect(request, pk):
    """Redirect from old pk-based URL to username-based URL."""
    user = get_object_or_404(CustomUser, pk=pk)
    return redirect(reverse("user-detail", kwargs={"username": user.username}), permanent=True)


def get_rate_limit_usage(user):
    limit = user.supporter_daily_limit or SUSTAINED_LIMIT
    cache_key = f"throttle_sustained_{user.pk}"
    history = cache.get(cache_key, [])
    now = time.time()
    used = sum(1 for ts in history if ts > now - SUSTAINED_DURATION)
    return {
        "limit": limit,
        "used": used,
        "remaining": max(0, limit - used),
        "percent_used": round(used / limit * 100, 1),
    }


class UserList(LoginRequiredMixin, ListView):
    model = CustomUser
    paginate_by = PAGINATE_BY
    queryset = CustomUser.objects.filter(is_active=True).order_by("username")


class SearchUserList(SearchMixin, UserList):
    def get_search_fields(self):
        return ["username__icontains", "first_name__icontains", "last_name__icontains"]


class UserProfile(LoginRequiredMixin, DetailView):
    model = CustomUser
    slug_field = "username"
    slug_url_kwarg = "username"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()

        # Add statistics to context
        context["stats"] = {
            "publishers": Publisher.objects.filter(created_by=user).count(),
            "series": Series.objects.filter(created_by=user).count(),
            "issues": Issue.objects.filter(created_by=user).count(),
            "characters": Character.objects.filter(created_by=user).count(),
            "creators": Creator.objects.filter(created_by=user).count(),
            "teams": Team.objects.filter(created_by=user).count(),
            "imprints": Imprint.objects.filter(created_by=user).count(),
            "arcs": Arc.objects.filter(created_by=user).count(),
            "universes": Universe.objects.filter(created_by=user).count(),
        }

        # Add daily API rate limit usage (only visible to the user themselves)
        if user.pk == self.request.user.pk:
            context["rate_limit"] = get_rate_limit_usage(user)
            context["is_supporter"] = user.is_supporter
            context["supporter_until"] = user.supporter_until
            context["supporter_tier_display"] = user.supporter_tier_display

        # Add recent reading history (last 10 items)
        context["recent_reads"] = (
            CollectionItem.objects.filter(user=user, is_read=True)
            .select_related(
                "issue__series__series_type",
                "issue__series__publisher",
            )
            .order_by("-date_read", "-modified")[:10]
        )

        return context

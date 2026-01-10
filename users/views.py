import logging

from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.views import PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.sites.shortcuts import get_current_site
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.generic import DetailView

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
from metron.utils import get_recaptcha_auth
from user_collection.models import CollectionItem
from users.forms import CustomUserChangeForm, CustomUserCreationForm
from users.models import CustomUser
from users.tokens import account_activation_token
from users.utils import send_pushover

logger = logging.getLogger(__name__)


def is_activated(user, token):
    return user is not None and account_activation_token.check_token(user, token)


def account_activation_sent(request):
    return render(request, "registration/account_activation_sent.html")


def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        return render(request, "registration/account_activation_invalid.html")

    if not is_activated(user, token):
        return render(request, "registration/account_activation_invalid.html")

    user.is_active = True
    user.email_confirmed = True
    user.save()
    login(request, user)
    # Send pushover notification tha user activated account
    send_pushover(f"{user} activated their account on Metron.")
    logger.info("%s activated their account on Metron", user)
    # Add a message asking the user to star the repository.
    msg = (
        "If you are planning on adding new information to the database, please refer to the "
        "<strong>Editing Guidelines</strong>.<br/><br/>"
        "If you have a GitHub account, the project would appreciate it if you could "
        "<strong>star</strong> the "
        "<a href='https://github.com/Metron-Project/metron'>Metron</a> repository. Thanks!"
    )
    messages.success(request, msg)

    return redirect("home")


def signup(request):  # sourcery skip: extract-method
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            result = get_recaptcha_auth(request)

            if result["success"]:
                user: CustomUser = form.save(commit=False)
                user.is_active = False
                user.save()
                current_site = get_current_site(request)
                subject = "Activate Your Metron Account"
                message = render_to_string(
                    "registration/account_activation_email.html",
                    {
                        "user": user,
                        "domain": current_site.domain,
                        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                        "token": account_activation_token.make_token(user),
                    },
                )
                user.email_user(subject, message)
                # Let's send a pushover notice that a user requested an account.
                send_pushover(f"{user} signed up for an account on Metron.")
                logger.info("%s signed up for an account on Metron", user)

            return redirect("account_activation_sent")
    else:
        form = CustomUserCreationForm()
    return render(request, "registration/signup.html", {"form": form})


class ChangePasswordView(SuccessMessageMixin, PasswordChangeView):
    template_name = "users/change_password.html"
    success_message = "Successfully Changed Your Password"
    success_url = reverse_lazy("home")


def change_profile(request):
    if not request.user.is_authenticated:
        return redirect("login")
    if request.method == "POST":
        form = CustomUserChangeForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, "Your profile was successfully updated!")
            return redirect("user-detail", pk=request.user.pk)
        messages.error(request, "Please correct the error below.")
    else:
        form = CustomUserChangeForm(instance=request.user)
    return render(request, "users/change_profile.html", {"form": form})


class UserProfile(DetailView):
    model = CustomUser

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

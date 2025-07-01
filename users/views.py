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

from metron.utils import get_recaptcha_auth
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
        user = None

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

from django.contrib.auth.views import LoginView
from django.urls import path, register_converter

from users import views
from users.converters import UsernameConverter
from users.forms import LoginForm

register_converter(UsernameConverter, "username")

urlpatterns = [
    # Shadows django.contrib.auth.urls' login (included after this module in
    # metron/urls.py) to report rate-limited logins as such.
    path("login/", LoginView.as_view(authentication_form=LoginForm), name="login"),
    path("signup/", views.signup, name="signup"),
    path(
        "account_activation_sent/",
        views.account_activation_sent,
        name="account_activation_sent",
    ),
    path("activate/<str:uidb64>/<str:token>/", views.activate, name="activate"),
    path("password/", views.ChangePasswordView.as_view(), name="change_password"),
    path("update/", views.change_profile, name="change_profile"),
    path(
        "email/confirm/<str:token>/",
        views.confirm_email_change,
        name="confirm_email_change",
    ),
    path("delete/", views.delete_account, name="delete_account"),
    path("tokens/", views.api_tokens, name="api_tokens"),
    path("tokens/<str:digest>/revoke/", views.revoke_api_token, name="revoke_api_token"),
    path("users/", views.UserList.as_view(), name="user-list"),
    path("search/", views.SearchUserList.as_view(), name="user-search"),
    path("<int:pk>/", views.user_profile_redirect, name="user-detail-redirect"),
    path("<username:username>/", views.UserProfile.as_view(), name="user-detail"),
]

from django.urls import path, register_converter

from users import views
from users.converters import UsernameConverter

register_converter(UsernameConverter, "username")

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path(
        "account_activation_sent/",
        views.account_activation_sent,
        name="account_activation_sent",
    ),
    path(
        r"activate/(?<uidb64>[0-9A-Za-z_\-]+)/(?<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/",
        views.activate,
        name="activate",
    ),
    path("password/", views.ChangePasswordView.as_view(), name="change_password"),
    path("update/", views.change_profile, name="change_profile"),
    path("<int:pk>/", views.user_profile_redirect, name="user-detail-redirect"),
    path("<username:username>/", views.UserProfile.as_view(), name="user-detail"),
]

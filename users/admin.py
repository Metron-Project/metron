from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from users.forms import CustomUserChangeForm, CustomUserCreationForm
from users.models import CustomUser, OpenCollectiveDonation


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = (
        "username",
        "email",
        "is_active",
        "email_confirmed",
        "supporter_until",
        "supporter_tier",
        "date_joined",
    )
    list_filter = (
        "is_staff",
        "is_superuser",
        "is_active",
        "email_confirmed",
        "supporter_tier",
        "date_joined",
        "groups",
    )
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            "Personal info",
            {"fields": ("first_name", "last_name", "email", "bio", "image")},
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "email_confirmed",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Supporter status", {"fields": ("supporter_until", "supporter_tier")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "password1", "password2"),
            },
        ),
    )


@admin.register(OpenCollectiveDonation)
class OpenCollectiveDonationAdmin(admin.ModelAdmin):
    list_display = ("transaction_id", "user", "email", "amount", "donated_at")
    list_filter = ("donated_at",)
    search_fields = ("transaction_id", "email", "user__username")
    ordering = ("-donated_at",)

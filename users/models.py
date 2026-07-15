from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from sorl.thumbnail import ImageField


class CustomUserManager(BaseUserManager):
    def _create_user(self, username, email, password=None, **extra_fields):
        if not username:
            raise ValueError("Users must have a username.")
        if not email:
            raise ValueError("Users must have an email address.")
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(username, email, password, **extra_fields)

    def create_superuser(self, username, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(username, email, password, **extra_fields)


class CustomUser(AbstractUser):
    email_confirmed = models.BooleanField(db_default=False)
    bio = models.TextField(blank=True)
    image = ImageField(upload_to="user/", blank=True)
    supporter_until = models.DateTimeField(blank=True, null=True)

    objects = CustomUserManager()

    def __str__(self):
        return self.username

    @property
    def is_supporter(self):
        return bool(self.supporter_until and self.supporter_until > timezone.now())


class OpenCollectiveDonation(models.Model):
    """A single processed OpenCollective contribution, used as an idempotency/audit record."""

    transaction_id = models.CharField(max_length=64, unique=True)
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="opencollective_donations",
    )
    email = models.EmailField()
    amount = models.IntegerField(help_text="Donation amount in cents.")
    donated_at = models.DateTimeField()
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.email} - {self.transaction_id}"

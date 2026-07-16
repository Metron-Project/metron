from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from sorl.thumbnail import ImageField

# (min_cents, slug, display_name, daily_limit), ordered by descending threshold so
# tier_for_amount can return on the first match ("round down to the nearest
# qualifying tier"). Mega Sponsor is a flat ceiling at $25+, not a per-dollar formula.
SUPPORTER_TIERS: tuple[tuple[int, str, str, int], ...] = (
    (2500, "mega_sponsor", "Mega Sponsor", 25000),
    (1000, "sponsor", "Sponsor", 15000),
    (500, "backer", "Backer", 10000),
    (200, "friend", "Friend", 7500),
)

_SUPPORTER_TIERS_BY_SLUG = {slug: (name, limit) for _, slug, name, limit in SUPPORTER_TIERS}


def tier_for_amount(cents: int) -> str | None:
    """Slug of the highest tier the amount qualifies for, or None if below Friend's minimum."""
    for min_cents, slug, _name, _limit in SUPPORTER_TIERS:
        if cents >= min_cents:
            return slug
    return None


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
    supporter_tier = models.CharField(
        max_length=20,
        blank=True,
        choices=[(slug, name) for _, slug, name, _ in reversed(SUPPORTER_TIERS)],
    )

    objects = CustomUserManager()

    def __str__(self):
        return self.username

    @property
    def is_supporter(self):
        return bool(self.supporter_until and self.supporter_until > timezone.now())

    @property
    def supporter_daily_limit(self) -> int | None:
        if not self.is_supporter:
            return None
        tier = _SUPPORTER_TIERS_BY_SLUG.get(self.supporter_tier)
        # Defensive fallback: is_supporter True but supporter_tier blank/unrecognized
        # shouldn't normally happen (the sync command always sets both together), but
        # fail open to the lowest tier (Friend) rather than silently granting nothing.
        return tier[1] if tier else SUPPORTER_TIERS[-1][3]

    @property
    def supporter_tier_display(self) -> str | None:
        if not self.is_supporter:
            return None
        tier = _SUPPORTER_TIERS_BY_SLUG.get(self.supporter_tier)
        return tier[0] if tier else SUPPORTER_TIERS[-1][2]


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
    frequency = models.CharField(
        max_length=10,
        blank=True,
        choices=[("monthly", "Monthly"), ("yearly", "Yearly"), ("onetime", "One-time")],
        help_text="The underlying OpenCollective order's frequency.",
    )
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.email} - {self.transaction_id}"

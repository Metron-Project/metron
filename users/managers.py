from django.db import models


class OnePerUserManager(models.Manager):
    """Manager for models with exactly one row per user (a ``user`` OneToOneField)."""

    def for_user(self, user):
        """Return ``user``'s row, creating it on first use.

        The returned object reuses ``user``, so accessing ``obj.user`` doesn't query.
        """
        obj, _created = self.get_or_create(user=user)
        obj.user = user
        return obj

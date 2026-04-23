from django.db import models
from django.db.models.functions import Now
from django.urls import reverse
from django.utils import timezone

from users.models import CustomUser


class Poll(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_polls",
    )
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    created_on = models.DateTimeField(db_default=Now())
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("polls:detail", args=[self.pk])

    @property
    def is_active(self):
        now = timezone.now()
        return self.start_date <= now <= self.end_date

    @property
    def is_upcoming(self):
        return timezone.now() < self.start_date

    @property
    def is_closed(self):
        return timezone.now() > self.end_date

    @property
    def status(self):
        if self.is_upcoming:
            return "upcoming"
        if self.is_active:
            return "active"
        return "closed"


class PollChoice(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "pk"]

    def __str__(self):
        return f"{self.poll.title}: {self.text}"


class PollVote(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="votes")
    choice = models.ForeignKey(PollChoice, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="poll_votes")
    voted_on = models.DateTimeField(db_default=Now())

    class Meta:
        unique_together = ["poll", "user"]

    def __str__(self):
        return f"{self.user.username} voted on {self.poll.title}"

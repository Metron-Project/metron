from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Case, Count, IntegerField, Value, When
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import DeleteView, DetailView, ListView

from polls.models import Poll, PollChoice, PollVote


class PollListView(ListView):
    model = Poll
    template_name = "polls/poll_list.html"
    context_object_name = "polls"
    paginate_by = 20

    def get_queryset(self):
        now = timezone.now()
        return (
            Poll.objects.annotate(
                vote_count=Count("votes"),
                status_order=Case(
                    When(start_date__lte=now, end_date__gte=now, then=Value(0)),
                    When(start_date__gt=now, then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField(),
                ),
            )
            .order_by("status_order", "-start_date")
            .select_related("created_by")
        )


class PollDetailView(DetailView):
    model = Poll
    template_name = "polls/poll_detail.html"
    context_object_name = "poll"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        poll = context["poll"]
        now = timezone.now()

        user_vote = None
        if self.request.user.is_authenticated:
            user_vote = PollVote.objects.filter(poll=poll, user=self.request.user).first()

        can_vote = (
            self.request.user.is_authenticated
            and poll.start_date <= now <= poll.end_date
            and user_vote is None
        )

        choices = poll.choices.annotate(vote_count=Count("votes")).order_by("order", "pk")
        total_votes = poll.votes.count()

        context["can_vote"] = can_vote
        context["user_vote"] = user_vote
        context["choices"] = choices
        context["total_votes"] = total_votes
        return context


class PollDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Poll
    template_name = "polls/poll_confirm_delete.html"
    success_url = reverse_lazy("polls:list")

    def test_func(self):
        return self.request.user.is_staff

    def form_valid(self, form):
        messages.success(self.request, f"Poll '{self.object.title}' deleted.")
        return super().form_valid(form)


@login_required
@require_POST
def vote(request, pk):
    poll = get_object_or_404(Poll, pk=pk)
    now = timezone.now()

    if not (poll.start_date <= now <= poll.end_date):
        return HttpResponseForbidden("Voting is not currently open for this poll.")

    if PollVote.objects.filter(poll=poll, user=request.user).exists():
        return HttpResponseForbidden("You have already voted in this poll.")

    choice_pk = request.POST.get("choice")
    if not choice_pk:
        return HttpResponseBadRequest("No choice selected.")

    choice = get_object_or_404(PollChoice, pk=choice_pk, poll=poll)
    PollVote.objects.create(poll=poll, choice=choice, user=request.user)

    choices = poll.choices.annotate(vote_count=Count("votes")).order_by("order", "pk")
    total_votes = poll.votes.count()
    user_vote = PollVote.objects.get(poll=poll, user=request.user)

    return render(
        request,
        "polls/partials/poll_results.html",
        {
            "poll": poll,
            "choices": choices,
            "total_votes": total_votes,
            "user_vote": user_vote,
        },
    )

import logging
from datetime import date, datetime
from typing import Any

from dal import autocomplete
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Prefetch, Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import DetailView, ListView, RedirectView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from comicsdb.filters.issue import IssueViewFilter
from comicsdb.forms.credits import CreditsFormSet
from comicsdb.forms.issue import IssueForm
from comicsdb.forms.variant import VariantFormset
from comicsdb.models import Creator, Credits, Issue, Role, Series
from comicsdb.models.series import SeriesType
from comicsdb.models.variant import Variant

PAGINATE = 28
TOTAL_WEEKS_YEAR = 52

LOGGER = logging.getLogger(__name__)


class SeriesAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Series.objects.none()

        qs = Series.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs


class CreatorAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Creator.objects.none()

        qs = Creator.objects.all()

        if self.q:
            qs = qs.filter(
                # Unaccent lookup won't work on alias array field.
                Q(name__unaccent__icontains=self.q) | Q(alias__icontains=self.q)
            )

        return qs


class IssueList(ListView):
    model = Issue
    paginate_by = PAGINATE
    # TODO: Let's look into limiting fields returned since we don't use most of them.
    queryset = Issue.objects.select_related("series", "series__series_type")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["series_type"] = SeriesType.objects.values("id", "name")
        return context


class IssueDetail(DetailView):
    model = Issue
    queryset = (
        Issue.objects.select_related("series", "series__publisher", "series__series_type", "rating")
        .defer(
            "created_on",
            "cover_hash",
            "series__desc",
            "series__modified",
            "series__created_on",
            "series__publisher__desc",
            "series__publisher__modified",
            "series__publisher__image",
            "series__publisher__founded",
            "series__publisher__created_on",
            "series__series_type__notes",
            "series__series_type__modified",
            "rating__description",
        )
        .prefetch_related(
            Prefetch(
                "credits_set",
                queryset=Credits.objects.select_related("creator")
                .defer(
                    "modified",
                    "creator__desc",
                    "creator__cv_id",
                    "creator__modified",
                    "creator__created_on",
                    "creator__birth",
                    "creator__death",
                    "creator__alias",
                )
                .order_by("creator__name")
                .distinct("creator__name")
                .prefetch_related(
                    Prefetch("role", queryset=Role.objects.defer("order", "notes", "modified"))
                ),
            ),
            Prefetch(
                "reprints",
                queryset=Issue.objects.select_related("series", "series__series_type")
                .defer(
                    "title",
                    "alt_number",
                    "desc",
                    "modified",
                    "name",
                    "price",
                    "rating",
                    "store_date",
                    "sku",
                    "isbn",
                    "upc",
                    "page",
                    "image",
                    "cover_hash",
                    "cv_id",
                    "gcd_id",
                    "created_by_id",
                    "edited_by_id",
                    "series__desc",
                    "series__cv_id",
                    "series__modified",
                    "series__created_on",
                    "series__year_end",
                    "series__series_type__notes",
                    "series__series_type__modified",
                )
                .order_by("cover_date", "store_date"),
            ),
        )
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        issue = self.get_object()
        try:
            next_issue = issue.get_next_by_cover_date(series=issue.series)
        except ObjectDoesNotExist:
            next_issue = None

        try:
            previous_issue = issue.get_previous_by_cover_date(series=issue.series)
        except ObjectDoesNotExist:
            previous_issue = None

        context["navigation"] = {
            "next_issue": next_issue,
            "previous_issue": previous_issue,
        }
        return context


class IssueDetailRedirect(RedirectView):
    def get_redirect_url(self, pk):
        issue = Issue.objects.get(pk=pk)
        return reverse("issue:detail", kwargs={"slug": issue.slug})


class SearchIssueList(IssueList):
    def get_queryset(self):
        result = super().get_queryset()
        issue_result = IssueViewFilter(self.request.GET, queryset=result)

        return issue_result.qs


class IssueCreate(LoginRequiredMixin, CreateView):
    model = Issue
    form_class = IssueForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["credits"] = CreditsFormSet(self.request.POST, prefix="credits")
            context["variants"] = VariantFormset(
                self.request.POST, self.request.FILES, prefix="variants"
            )
        else:
            context["credits"] = CreditsFormSet(prefix="credits")
            context["variants"] = VariantFormset(prefix="variants")
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        credits_form = context["credits"]
        variants_form = context["variants"]
        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.edited_by = self.request.user
            self.object = form.save()

            if credits_form.is_valid() and variants_form.is_valid():
                credits_form.instance = self.object
                credits_form.save()
                variants_form.instance = self.object
                variants_form.save()

            LOGGER.info(
                "Issue: %s #%s was created by %s",
                form.instance.series,
                form.instance.number,
                self.request.user,
            )
        return super().form_valid(form)


class IssueUpdate(LoginRequiredMixin, UpdateView):
    model = Issue
    form_class = IssueForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["credits"] = CreditsFormSet(
                self.request.POST,
                instance=self.object,
                queryset=(Credits.objects.filter(issue=self.object).prefetch_related("role")),
                prefix="credits",
            )
            context["variants"] = VariantFormset(
                self.request.POST,
                self.request.FILES,
                instance=self.object,
                queryset=(Variant.objects.filter(issue=self.object)),
                prefix="variants",
            )
            context["credits"].full_clean()
            context["variants"].full_clean()
        else:
            context["credits"] = CreditsFormSet(
                instance=self.object,
                queryset=(Credits.objects.filter(issue=self.object).prefetch_related("role")),
                prefix="credits",
            )
            context["variants"] = VariantFormset(
                instance=self.object,
                queryset=(Variant.objects.filter(issue=self.object)),
                prefix="variants",
            )
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        credits_form = context["credits"]
        variants_form = context["variants"]
        with transaction.atomic():
            form.instance.edited_by = self.request.user
            self.object = form.save(commit=False)

            if credits_form.is_valid() and variants_form.is_valid():
                credits_form.instance = self.object
                variants_form.instance = self.object
                credits_form.save()
                variants_form.save()
            else:
                return super().form_invalid(form)

            LOGGER.info(
                "Issue: %s #%s was updated by %s",
                form.instance.series,
                form.instance.number,
                self.request.user,
            )
        return super().form_valid(form)


class IssueReprintSyncView(LoginRequiredMixin, View):
    """
    View to synchronize characters and teams from reprinted issues
    to the current issue.
    """

    def post(self, request, slug):  # noqa: PLR0912
        """
        Add characters, teams, and story titles from all reprinted issues to the current issue.
        Only works for Trade Paperback, Omnibus, and Hardcover series types.
        Only syncs issues with one story title or less.
        Only syncs if the issue has no existing characters, teams, or stories.

        For story titles: If a reprinted issue has a story title, it's added.
        If no story title exists, "[Untitled]" is added instead.

        Args:
            request: HTTP request object
            slug: Issue slug identifier

        Returns:
            HttpResponseRedirect to the issue detail page
        """
        issue = get_object_or_404(
            Issue.objects.select_related("series", "series__series_type").prefetch_related(
                "reprints", "reprints__characters", "reprints__teams", "characters", "teams"
            ),
            slug=slug,
        )

        # Check if series type is Trade Paperback or Omnibus
        allowed_types = ["Trade Paperback", "Omnibus", "Hardcover"]
        if issue.series.series_type.name not in allowed_types:
            messages.error(
                request,
                f"This function only works for {', '.join(allowed_types[:-1])} "
                f"and {allowed_types[-1]} series types. "
                f"This issue is of type '{issue.series.series_type.name}'.",
            )
            return HttpResponseRedirect(reverse("issue:detail", args=[slug]))

        # Check if there are any reprints
        if not issue.reprints.exists():
            messages.warning(request, f"No reprinted issues found for {issue}.")
            return HttpResponseRedirect(reverse("issue:detail", args=[slug]))

        # Check if issue already has characters, teams, or stories
        has_stories = issue.name and len(issue.name) > 0
        if issue.characters.exists() or issue.teams.exists() or has_stories:
            messages.info(
                request,
                f"{issue} already has characters, teams, or stories assigned. "
                "Sync operation cancelled to preserve existing data.",
            )
            return HttpResponseRedirect(reverse("issue:detail", args=[slug]))

        # Collect all characters and teams from reprints
        # Only include reprints with one story title or less
        characters_to_add = set()
        teams_to_add = set()
        stories_to_add = []
        skipped_reprints = []

        for reprint in issue.reprints.all():
            story_count = len(reprint.name) if reprint.name else 0
            if story_count > 1:
                skipped_reprints.append(str(reprint))
                continue

            characters_to_add.update(reprint.characters.all())
            teams_to_add.update(reprint.teams.all())

            # Add story title or [Untitled] if no story
            if reprint.name and len(reprint.name) > 0:
                stories_to_add.append(reprint.name[0])
            else:
                stories_to_add.append("[Untitled]")

        # Inform user if any reprints were skipped
        if skipped_reprints:
            messages.warning(
                request,
                f"Skipped {len(skipped_reprints)} reprinted issue(s) with multiple story titles: "
                f"{', '.join(skipped_reprints[:3])}"
                f"{'...' if len(skipped_reprints) > 3 else ''}",  # noqa: PLR2004
            )

        # Check if we found any characters or teams to add
        if not characters_to_add and not teams_to_add:
            messages.info(request, "No characters or teams found in the reprinted issues.")
            return HttpResponseRedirect(reverse("issue:detail", args=[slug]))

        # Add all characters, teams, and stories from reprints
        with transaction.atomic():
            if characters_to_add:
                issue.characters.add(*characters_to_add)
                LOGGER.info(
                    "Added %d characters to %s from reprints by %s",
                    len(characters_to_add),
                    issue,
                    request.user,
                )

            if teams_to_add:
                issue.teams.add(*teams_to_add)
                LOGGER.info(
                    "Added %d teams to %s from reprints by %s",
                    len(teams_to_add),
                    issue,
                    request.user,
                )

            # Add stories to the issue's name field
            if stories_to_add:
                issue.name = stories_to_add
                LOGGER.info(
                    "Added %d story title(s) to %s from reprints by %s",
                    len(stories_to_add),
                    issue,
                    request.user,
                )

            # Update edited_by field
            issue.edited_by = request.user
            issue.save(update_fields=["edited_by", "modified", "name"])

        # Provide feedback
        message_parts = []
        if characters_to_add:
            message_parts.append(f"{len(characters_to_add)} character(s)")
        if teams_to_add:
            message_parts.append(f"{len(teams_to_add)} team(s)")
        if stories_to_add:
            message_parts.append(f"{len(stories_to_add)} story title(s)")

        messages.success(
            request,
            f"Successfully added {', '.join(message_parts[:-1])} and "
            f"{message_parts[-1]} from reprinted issues."
            if len(message_parts) > 1
            else f"Successfully added {message_parts[0]} from reprinted issues.",
        )

        return HttpResponseRedirect(reverse("issue:detail", args=[slug]))


class IssueDelete(PermissionRequiredMixin, DeleteView):
    model = Issue
    template_name = "comicsdb/confirm_delete.html"
    permission_required = "comicsdb.delete_issue"
    success_url = reverse_lazy("issue:list")


class WeekList(ListView):
    year, week, _ = date.today().isocalendar()

    model = Issue
    paginate_by = PAGINATE
    template_name = "comicsdb/week_list.html"
    queryset = (
        Issue.objects.filter(store_date__week=week)
        .filter(store_date__year=year)
        .prefetch_related("series", "series__series_type")
    )

    def get_context_data(self, **kwargs):
        # The '1' in the format string gives the date for Monday
        release_day = datetime.strptime(f"{self.year}-{self.week}-1", "%G-%V-%u")
        context = super().get_context_data(**kwargs)
        context["release_day"] = release_day
        context["future"] = False
        context["series_type"] = SeriesType.objects.values("id", "name")
        return context


class NextWeekList(ListView):
    year, week, _ = date.today().isocalendar()
    # Check if we're at the last week of the year.
    if week != TOTAL_WEEKS_YEAR:
        week += 1
    else:
        year += 1
        week = 1

    model = Issue
    paginate_by = PAGINATE
    template_name = "comicsdb/week_list.html"
    queryset = (
        Issue.objects.filter(store_date__week=week)
        .filter(store_date__year=year)
        .prefetch_related("series", "series__series_type")
    )

    def get_context_data(self, **kwargs):
        # The '1' in the format string gives the date for Monday
        release_day = datetime.strptime(f"{self.year}-{self.week}-1", "%G-%V-%u")
        context = super().get_context_data(**kwargs)
        context["release_day"] = release_day
        context["future"] = False
        context["series_type"] = SeriesType.objects.values("id", "name")
        return context


# View to show any issues released after next weeks.
class FutureList(ListView):
    year, week, _ = date.today().isocalendar()
    # Check if we're at the last week of the year.
    if week != TOTAL_WEEKS_YEAR:
        week += 1
    else:
        year += 1
        week = 1

    model = Issue
    paginate_by = PAGINATE
    template_name = "comicsdb/week_list.html"
    queryset = (
        Issue.objects.filter(store_date__year__gte=year)
        .exclude(store_date__week__lte=week, store_date__year=year)
        .prefetch_related("series", "series__series_type")
    )

    def get_context_data(self, **kwargs):
        # The '1' in the format string gives the date for Monday
        release_day = datetime.strptime(f"{self.year}-{self.week}-1", "%G-%V-%u")
        context = super().get_context_data(**kwargs)
        context["release_day"] = release_day
        context["future"] = True
        context["series_type"] = SeriesType.objects.values("id", "name")
        return context

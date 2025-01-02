import logging
from datetime import date, datetime
from typing import Any

from dal import autocomplete
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Prefetch, Q
from django.urls import reverse, reverse_lazy
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
        Issue.objects.select_related(
            "series", "series__publisher", "series__series_type", "rating"
        )
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
        return reverse("character:detail", kwargs={"slug": issue.slug})


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

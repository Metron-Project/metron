import logging
from dataclasses import dataclass, field
from datetime import date

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, DecimalField, Prefetch
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from comicsdb.filters.issue import IssueViewFilter
from comicsdb.forms.attribution import AttributionFormSet
from comicsdb.forms.credits import CreditsFormSet
from comicsdb.forms.issue import MINIMUM_YEAR, IssueForm
from comicsdb.forms.variant import VariantFormset
from comicsdb.models import Credits, Issue, Role
from comicsdb.models.attribution import Attribution
from comicsdb.models.variant import Variant
from comicsdb.release_week import release_week_bounds
from comicsdb.views.constants import DETAIL_PAGINATE_BY, PAGINATE_BY
from comicsdb.views.history import HistoryListView
from comicsdb.views.issue_list_helpers import apply_sort
from comicsdb.views.mixins import FilterableIssueListMixin, LazyLoadMixin, SlugRedirectView
from issue_ratings.models import IssueRating
from wish_list.models import WishListItem

LOGGER = logging.getLogger(__name__)


class IssueList(FilterableIssueListMixin, ListView):
    model = Issue
    paginate_by = PAGINATE_BY

    def get_queryset(self):
        queryset = Issue.objects.select_related(
            "series", "series__series_type", "series__publisher"
        )
        # Apply filters
        filtered = IssueViewFilter(self.request.GET, queryset=queryset)
        return apply_sort(filtered.qs, self.request)


class IssueDetail(DetailView):
    model = Issue
    queryset = (
        Issue.objects.select_related(
            "series", "series__publisher", "series__series_type", "rating", "edited_by"
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
            "characters",
            "teams",
            "universes",
        )
    )

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .annotate(
                average_rating=Avg(
                    "ratings__rating", output_field=DecimalField(max_digits=3, decimal_places=2)
                ),
                rating_count=Count("ratings", distinct=True),
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        issue = context["object"]

        try:
            next_issue = issue.get_next_by_cover_date(series=issue.series)
            next_issue.series = issue.series
        except ObjectDoesNotExist:
            next_issue = None

        try:
            previous_issue = issue.get_previous_by_cover_date(series=issue.series)
            previous_issue.series = issue.series
        except ObjectDoesNotExist:
            previous_issue = None

        context["navigation"] = {
            "next_issue": next_issue,
            "previous_issue": previous_issue,
        }

        # Get counts for pagination
        credits_qs = (
            Credits.objects.filter(issue=issue)
            .select_related("creator")
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
            )
        )
        credits_count = credits_qs.count()
        context["credits_count"] = credits_count
        if credits_count > 0:
            context["credits"] = credits_qs[:DETAIL_PAGINATE_BY]

        characters = list(issue.characters.all())
        characters_count = len(characters)
        context["characters_count"] = characters_count
        if characters_count > 0:
            context["characters"] = characters[:DETAIL_PAGINATE_BY]

        teams = list(issue.teams.all())
        teams_count = len(teams)
        context["teams_count"] = teams_count
        if teams_count > 0:
            context["teams"] = teams[:DETAIL_PAGINATE_BY]

        universes = list(issue.universes.all())
        universes_count = len(universes)
        context["universes_count"] = universes_count
        if universes_count > 0:
            context["universes"] = universes[:DETAIL_PAGINATE_BY]

        if self.request.user.is_authenticated:
            context["on_wish_list"] = WishListItem.objects.filter(
                wish_list__user=self.request.user,
                issue=issue,
            ).exists()
            context["user_rating"] = IssueRating.objects.filter(
                issue=issue,
                user=self.request.user,
            ).first()

        context["can_rate"] = self.request.user.is_authenticated and issue.is_released
        context["average_rating"] = issue.average_rating
        context["rating_count"] = issue.rating_count

        return context


class IssueDetailRedirect(SlugRedirectView):
    model = Issue
    url_name = "issue:detail"


class SearchIssueList(IssueList):
    """
    Legacy search view for backward compatibility with existing bookmarks/links.
    The main IssueList view now handles all filtering.
    """


class IssueCreate(LoginRequiredMixin, CreateView):
    model = Issue
    form_class = IssueForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["minimum_year"] = MINIMUM_YEAR
        # Formsets passed in (already validated by form_valid) are kept so their errors show.
        if "credits" not in context:
            if self.request.POST:
                context["credits"] = CreditsFormSet(self.request.POST, prefix="credits")
                context["variants"] = VariantFormset(
                    self.request.POST, self.request.FILES, prefix="variants"
                )
                context["attribution"] = AttributionFormSet(self.request.POST, prefix="attribution")
            else:
                context["credits"] = CreditsFormSet(prefix="credits")
                context["variants"] = VariantFormset(prefix="variants")
                context["attribution"] = AttributionFormSet(prefix="attribution")
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        credits_form = context["credits"]
        variants_form = context["variants"]
        attribution_form = context["attribution"]
        # Validate against the unsaved issue so variant UPCs are checked against its cover date.
        variants_form.instance = form.instance
        formsets_valid = [
            formset.is_valid() for formset in (credits_form, variants_form, attribution_form)
        ]
        if not all(formsets_valid):
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    credits=credits_form,
                    variants=variants_form,
                    attribution=attribution_form,
                )
            )
        try:
            with transaction.atomic():
                form.instance.created_by = self.request.user
                form.instance.edited_by = self.request.user
                self.object = form.save()
                credits_form.instance = self.object
                credits_form.save()
                variants_form.instance = self.object
                variants_form.save()
                attribution_form.instance = self.object
                attribution_form.save()

                LOGGER.info(
                    "Issue: %s #%s was created by %s",
                    form.instance.series,
                    form.instance.number,
                    self.request.user,
                )
        except IntegrityError:
            form.add_error(
                None,
                "An issue with this series and number already exists. "
                "It may have been created by another user.",
            )
            return self.form_invalid(form)
        # Not super().form_valid(): it would call form.save() a second time.
        return HttpResponseRedirect(self.get_success_url())


class IssueUpdate(LoginRequiredMixin, UpdateView):
    model = Issue
    form_class = IssueForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["minimum_year"] = MINIMUM_YEAR
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
            context["attribution"] = AttributionFormSet(
                self.request.POST,
                instance=self.object,
                queryset=(Attribution.objects.filter(issues=self.object)),
                prefix="attribution",
            )
            context["credits"].full_clean()
            context["variants"].full_clean()
            context["attribution"].full_clean()
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
            context["attribution"] = AttributionFormSet(
                instance=self.object,
                queryset=(Attribution.objects.filter(issues=self.object)),
                prefix="attribution",
            )
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        credits_form = context["credits"]
        variants_form = context["variants"]
        attribution_form = context["attribution"]
        with transaction.atomic():
            form.instance.edited_by = self.request.user
            self.object = form.save(commit=False)

            if credits_form.is_valid() and variants_form.is_valid() and attribution_form.is_valid():
                credits_form.instance = self.object
                variants_form.instance = self.object
                attribution_form.instance = self.object
                credits_form.save()
                variants_form.save()
                attribution_form.save()
            else:
                return super().form_invalid(form)

            LOGGER.info(
                "Issue: %s #%s was updated by %s",
                form.instance.series,
                form.instance.number,
                self.request.user,
            )
        return super().form_valid(form)


class IssueFormsetAddRowView(LoginRequiredMixin, View):
    """Base view for adding new formset rows via HTMX."""

    formset_class = None
    template_name = None
    prefix = None

    def get(self, request):
        """Return a new empty form row."""
        # Get the form index from the request
        form_idx = int(request.GET.get("form_idx", 0))

        # Create a formset with one empty form
        formset = self.formset_class(prefix=self.prefix)

        # Get the empty form and set its index
        form = formset.empty_form
        form_html = render_to_string(
            self.template_name,
            {
                "form": form,
                "form_idx": form_idx,
                "prefix": self.prefix,
            },
        )

        # Replace __prefix__ placeholder with the actual form index
        form_html = form_html.replace(f"{self.prefix}-__prefix__", f"{self.prefix}-{form_idx}")

        return HttpResponse(form_html)


class IssueCreditsAddRowView(IssueFormsetAddRowView):
    """HTMX endpoint for adding a new credit form row."""

    formset_class = CreditsFormSet
    template_name = "comicsdb/partials/credits_formset_row.html"
    prefix = "credits"


class IssueVariantsAddRowView(IssueFormsetAddRowView):
    """HTMX endpoint for adding a new variant form row."""

    formset_class = VariantFormset
    template_name = "comicsdb/partials/variants_formset_row.html"
    prefix = "variants"


class IssueAttributionAddRowView(IssueFormsetAddRowView):
    """HTMX endpoint for adding a new attribution form row."""

    formset_class = AttributionFormSet
    template_name = "comicsdb/partials/attribution_formset_row.html"
    prefix = "attribution"


class IssueDuplicateCreditsView(LoginRequiredMixin, View):
    """
    View to duplicate credits from the previous issue in the same series.
    """

    def post(self, request, slug):
        """
        Copy all credits (creators and their roles) from the previous issue
        to the current issue. Only works if the current issue has no existing credits.

        Args:
            request: HTTP request object
            slug: Issue slug identifier

        Returns:
            HttpResponseRedirect to the issue detail page
        """
        issue = get_object_or_404(
            Issue.objects.select_related("series", "series__publisher").prefetch_related(
                "credits_set"
            ),
            slug=slug,
        )

        # Check if publisher is DC Comics or Marvel (not allowed for credit duplication)
        excluded_publishers = ["DC Comics", "Marvel"]
        if issue.series.publisher.name in excluded_publishers:
            messages.error(
                request,
                _("Credit duplication is not allowed for %(publisher)s issues.")
                % {"publisher": issue.series.publisher.name},
            )
            return HttpResponseRedirect(reverse("issue:detail", args=[slug]))

        # Check if issue already has credits
        if issue.credits_set.exists():
            messages.info(
                request,
                _(
                    "%(issue)s already has credits assigned. "
                    "Duplicate operation cancelled to preserve existing data."
                )
                % {"issue": issue},
            )
            return HttpResponseRedirect(reverse("issue:detail", args=[slug]))

        # Try to get the previous issue by cover_date
        try:
            previous_issue = issue.get_previous_by_cover_date(series=issue.series)
        except ObjectDoesNotExist:
            messages.warning(
                request, _("No previous issue found for %(issue)s.") % {"issue": issue}
            )
            return HttpResponseRedirect(reverse("issue:detail", args=[slug]))

        # Get all credits from the previous issue
        previous_credits = Credits.objects.filter(issue=previous_issue).prefetch_related("role")

        if not previous_credits.exists():
            messages.info(
                request,
                _("No credits found in %(issue)s to duplicate.") % {"issue": previous_issue},
            )
            return HttpResponseRedirect(reverse("issue:detail", args=[slug]))

        # Get the Cover role to check for variant cover credits
        try:
            cover_role = Role.objects.get(name="Cover")
        except Role.DoesNotExist:
            cover_role = None

        # Duplicate the credits
        credits_count = 0
        skipped_count = 0
        max_roles_for_cover_skip = 2

        with transaction.atomic():
            for credit in previous_credits:
                roles = credit.role.all()

                # Skip credits that are likely variant cover credits
                # (credits with only one role and that role is "Cover")
                if cover_role and len(roles) < max_roles_for_cover_skip and cover_role in roles:
                    skipped_count += 1
                    LOGGER.info(
                        "Skipping possible variant cover credit for '%s' when duplicating to %s",
                        credit.creator,
                        issue,
                    )
                    continue

                # Create new credit for current issue
                new_credit = Credits.objects.create(issue=issue, creator=credit.creator)
                # Copy the roles (many-to-many relationship)
                new_credit.role.set(roles)
                credits_count += 1

            # Update edited_by field
            issue.edited_by = request.user
            issue.save(update_fields=["edited_by", "modified"])

            LOGGER.info(
                "Duplicated %d credit(s) from %s to %s by %s (skipped %d cover credit(s))",
                credits_count,
                previous_issue,
                issue,
                request.user,
                skipped_count,
            )

        # Provide appropriate feedback based on what was duplicated
        if credits_count > 0:
            if skipped_count > 0:
                message = _(
                    "Successfully duplicated %(credits)s credit(s) from %(issue)s."
                    " Skipped %(skipped)s variant cover credit(s)."
                ) % {
                    "credits": credits_count,
                    "issue": previous_issue,
                    "skipped": skipped_count,
                }
            else:
                message = _("Successfully duplicated %(credits)s credit(s) from %(issue)s.") % {
                    "credits": credits_count,
                    "issue": previous_issue,
                }
            messages.success(request, message)
        elif skipped_count > 0:
            messages.info(
                request,
                _(
                    "No credits were duplicated. Skipped %(skipped)s variant cover credit(s)"
                    " from %(issue)s."
                )
                % {"skipped": skipped_count, "issue": previous_issue},
            )
        else:
            messages.info(
                request,
                _("No credits found in %(issue)s to duplicate.") % {"issue": previous_issue},
            )

        return HttpResponseRedirect(reverse("issue:detail", args=[slug]))


REPRINT_SYNC_SERIES_TYPES = ("Trade Paperback", "Omnibus", "Hardcover")
# How many skipped reprint names to list in the warning before truncating.
MAX_SKIPPED_REPRINT_NAMES = 3


@dataclass
class ReprintContent:
    """Characters, teams and story titles gathered from an issue's reprints."""

    characters: set = field(default_factory=set)
    teams: set = field(default_factory=set)
    stories: list[str] = field(default_factory=list)
    skipped_reprints: list[str] = field(default_factory=list)


def reprint_sync_blocker(issue: Issue) -> tuple[int, str] | None:
    """Return ``(message_level, message)`` if ``issue`` can't be synced, else ``None``."""
    series_type = issue.series.series_type.name
    if series_type not in REPRINT_SYNC_SERIES_TYPES:
        types = REPRINT_SYNC_SERIES_TYPES
        type_list = f"{', '.join(types[:-1])} and {types[-1]}"
        return messages.ERROR, _(
            "This function only works for %(types)s series types. "
            "This issue is of type '%(current_type)s'."
        ) % {"types": type_list, "current_type": series_type}

    if not issue.reprints.exists():
        return messages.WARNING, _("No reprinted issues found for %(issue)s.") % {"issue": issue}

    if issue.characters.exists() or issue.teams.exists() or issue.name:
        return messages.INFO, _(
            "%(issue)s already has characters, teams, or stories assigned. "
            "Sync operation cancelled to preserve existing data."
        ) % {"issue": issue}

    return None


def collect_reprint_content(issue: Issue) -> ReprintContent:
    """Gather characters, teams and story titles from ``issue``'s reprints.

    Reprints with more than one story title are skipped. A reprint with no story
    title contributes "[Untitled]".
    """
    content = ReprintContent()
    for reprint in issue.reprints.all():
        if reprint.name and len(reprint.name) > 1:
            content.skipped_reprints.append(str(reprint))
            continue
        content.characters.update(reprint.characters.all())
        content.teams.update(reprint.teams.all())
        content.stories.append(reprint.name[0] if reprint.name else "[Untitled]")
    return content


def apply_reprint_content(issue: Issue, content: ReprintContent, user) -> None:
    """Add ``content`` to ``issue`` and record ``user`` as its editor."""
    with transaction.atomic():
        if content.characters:
            issue.characters.add(*content.characters)
            LOGGER.info(
                "Added %d characters to %s from reprints by %s",
                len(content.characters),
                issue,
                user,
            )

        if content.teams:
            issue.teams.add(*content.teams)
            LOGGER.info("Added %d teams to %s from reprints by %s", len(content.teams), issue, user)

        if content.stories:
            issue.name = content.stories
            LOGGER.info(
                "Added %d story title(s) to %s from reprints by %s",
                len(content.stories),
                issue,
                user,
            )

        issue.edited_by = user
        issue.save(update_fields=["edited_by", "modified", "name"])


def _reprint_sync_summary(content: ReprintContent) -> str:
    """Return e.g. "3 character(s), 1 team(s) and 2 story title(s)"."""
    parts = []
    if content.characters:
        parts.append(_("%(count)s character(s)") % {"count": len(content.characters)})
    if content.teams:
        parts.append(_("%(count)s team(s)") % {"count": len(content.teams)})
    if content.stories:
        parts.append(_("%(count)s story title(s)") % {"count": len(content.stories)})

    if len(parts) > 1:
        return _("%(first)s and %(last)s") % {"first": ", ".join(parts[:-1]), "last": parts[-1]}
    return parts[0]


class IssueReprintSyncView(LoginRequiredMixin, View):
    """
    View to synchronize characters and teams from reprinted issues
    to the current issue.
    """

    def post(self, request, slug):
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
        redirect = HttpResponseRedirect(reverse("issue:detail", args=[slug]))
        issue = get_object_or_404(
            Issue.objects.select_related("series", "series__series_type").prefetch_related(
                "reprints", "reprints__characters", "reprints__teams", "characters", "teams"
            ),
            slug=slug,
        )

        if blocker := reprint_sync_blocker(issue):
            level, message = blocker
            messages.add_message(request, level, message)
            return redirect

        content = collect_reprint_content(issue)

        if skipped := content.skipped_reprints:
            reprint_names = ", ".join(skipped[:MAX_SKIPPED_REPRINT_NAMES])
            if len(skipped) > MAX_SKIPPED_REPRINT_NAMES:
                reprint_names += "..."
            messages.warning(
                request,
                _("Skipped %(count)s reprinted issue(s) with multiple story titles: %(names)s")
                % {"count": len(skipped), "names": reprint_names},
            )

        if not content.characters and not content.teams:
            messages.info(request, _("No characters or teams found in the reprinted issues."))
            return redirect

        apply_reprint_content(issue, content, request.user)

        messages.success(
            request,
            _("Successfully added %(parts)s from reprinted issues.")
            % {"parts": _reprint_sync_summary(content)},
        )
        return redirect


class IssueDelete(PermissionRequiredMixin, DeleteView):
    model = Issue
    template_name = "comicsdb/confirm_delete.html"
    permission_required = "comicsdb.delete_issue"
    success_url = reverse_lazy("issue:list")


class IssueHistory(HistoryListView):
    model = Issue


class _ReleaseWeekListBase(FilterableIssueListMixin, ListView):
    """Issues by store date, relative to an ISO week (Monday-Sunday).

    Subclasses set ``week_offset`` (0 = this week, 1 = next week) and ``future``.
    A non-future view lists that week's issues; a future view lists everything
    released after it.
    """

    model = Issue
    paginate_by = PAGINATE_BY
    template_name = "comicsdb/week_list.html"
    week_offset = 0
    future = False

    def get_week_start(self) -> date:
        """Return the Monday of the target ISO week."""
        return release_week_bounds(self.week_offset)[0]

    def get_queryset(self):
        week_start, week_end = release_week_bounds(self.week_offset)
        if self.future:
            queryset = Issue.objects.filter(store_date__gt=week_end)
        else:
            queryset = Issue.objects.filter(store_date__gte=week_start, store_date__lte=week_end)
        queryset = queryset.select_related("series", "series__series_type", "series__publisher")
        filtered = IssueViewFilter(self.request.GET, queryset=queryset)
        return apply_sort(filtered.qs, self.request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["release_day"] = self.get_week_start()
        context["future"] = self.future
        return context


class WeekList(_ReleaseWeekListBase):
    """Issues released this week."""


class NextWeekList(_ReleaseWeekListBase):
    """Issues released next week."""

    week_offset = 1


class FutureList(_ReleaseWeekListBase):
    """Issues released after next week."""

    week_offset = 1
    future = True


class IssueCreditsLoadMore(LazyLoadMixin):
    """HTMX endpoint for lazy loading more issue credits."""

    model = Issue
    relation_name = None  # Custom query with optimizations
    template_name = "comicsdb/partials/issue_credit_items.html"
    context_object_name = "credits"
    slug_context_name = "issue_slug"

    def get_queryset(self, parent_object, offset, limit):
        """Custom query with select_related, defer, and prefetch optimizations."""
        credits_qs = (
            Credits.objects.filter(issue=parent_object)
            .select_related("creator")
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
            )
        )
        return credits_qs[offset : offset + limit]

    def get_total_count(self, parent_object):
        """Get total count of credits."""
        return (
            Credits.objects.filter(issue=parent_object)
            .order_by("creator__name")
            .distinct("creator__name")
            .count()
        )


class IssueCharactersLoadMore(LazyLoadMixin):
    """HTMX endpoint for lazy loading more issue characters."""

    model = Issue
    relation_name = "characters"
    template_name = "comicsdb/partials/issue_character_items.html"
    context_object_name = "characters"
    slug_context_name = "issue_slug"


class IssueTeamsLoadMore(LazyLoadMixin):
    """HTMX endpoint for lazy loading more issue teams."""

    model = Issue
    relation_name = "teams"
    template_name = "comicsdb/partials/issue_team_items.html"
    context_object_name = "teams"
    slug_context_name = "issue_slug"


class IssueUniversesLoadMore(LazyLoadMixin):
    """HTMX endpoint for lazy loading more issue universes."""

    model = Issue
    relation_name = "universes"
    template_name = "comicsdb/partials/issue_universe_items.html"
    context_object_name = "universes"
    slug_context_name = "issue_slug"

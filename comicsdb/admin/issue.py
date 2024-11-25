import datetime
from typing import Any

from django.contrib import admin, messages
from django.db.models.query import QuerySet
from django.utils.translation import ngettext
from sorl.thumbnail.admin.current import AdminImageMixin

from comicsdb.admin.util import AttributionInline
from comicsdb.models import Creator, Credits, Issue, Rating, Role, Variant

MAX_STORIES = 1


class FutureStoreDateListFilter(admin.SimpleListFilter):
    title = "future store week"

    parameter_name = "store_date"

    def lookups(self, request: Any, model_admin: Any):
        return (("thisWeek", "This week"), ("nextWeek", "Next week"))

    def queryset(self, request: Any, queryset: QuerySet) -> QuerySet | None:
        today = datetime.date.today()
        year, week, _ = today.isocalendar()

        match self.value():
            case "thisWeek":
                return queryset.filter(store_date__week=week, store_date__year=year)
            case "nextWeek":
                return queryset.filter(store_date__week=week + 1, store_date__year=year)
            case _:
                return None


class CreatedOnDateListFilter(admin.SimpleListFilter):
    title = "created on"

    parameter_name = "created_on"

    def lookups(self, request: Any, model_admin: Any):
        return (
            ("today", "Today"),
            ("yesterday", "Yesterday"),
            ("7day", "Past 7 days"),
            ("thisMonth", "This month"),
            ("thisYear", "This year"),
        )

    def queryset(self, request: Any, queryset: QuerySet[Any]) -> QuerySet[Any] | None:
        # sourcery skip: use-datetime-now-not-today
        today = datetime.date.today()
        yesterday = datetime.datetime.today() - datetime.timedelta(days=1)
        last_week = datetime.datetime.today() - datetime.timedelta(days=7)

        match self.value():
            case "today":
                return queryset.filter(created_on__date=today)
            case "yesterday":
                return queryset.filter(created_on__date=yesterday.date())
            case "7day":
                return queryset.filter(created_on__date__gte=last_week.date())
            case "thisMonth":
                return queryset.filter(
                    created_on__year=today.year, created_on__month=today.month
                )
            case "thisYear":
                return queryset.filter(created_on__year=today.year)
            case _:
                return None


class CreditsInline(admin.TabularInline):
    model = Credits
    autocomplete_fields = ["creator"]
    extra = 1


class VariantInline(admin.TabularInline):
    model = Variant
    extra = 1


@admin.register(Issue)
class IssueAdmin(AdminImageMixin, admin.ModelAdmin):
    search_fields = ("series__name", "number")
    list_display = ("__str__", "cover_date", "store_date", "created_on")
    list_filter = (
        FutureStoreDateListFilter,
        CreatedOnDateListFilter,
        "modified",
        "store_date",
        "cover_date",
        "series__publisher",
    )
    autocomplete_fields = ["series", "characters", "teams", "arcs", "universes", "reprints"]
    list_select_related = ("series",)
    date_hierarchy = "cover_date"
    actions = [
        "add_teen_rating",
        "add_dc_credits",
        "add_marvel_credits",
        "add_reprint_info",
        "remove_cover",
    ]
    actions_on_top = True
    # form view
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "series",
                    "number",
                    "slug",
                    "name",
                    "title",
                    "cover_date",
                    "store_date",
                    "price",
                    "rating",
                    "sku",
                    "isbn",
                    "upc",
                    "page",
                    "desc",
                    "characters",
                    "teams",
                    "arcs",
                    "universes",
                    "reprints",
                    "cv_id",
                    "image",
                    "created_by",
                    "edited_by",
                )
            },
        ),
    )
    inlines = (CreditsInline, VariantInline, AttributionInline)

    @admin.action(description="Remove cover from selected issues")
    def remove_cover(self, request, queryset) -> None:
        count = 0
        for issue in queryset:
            if issue.image:
                issue.image.delete(save=True)
                count += 1

        self.message_user(
            request,
            ngettext("%d issue was updated.", "%d issues were updated.", count) % count,
            messages.SUCCESS,
        )

    @admin.action(description="Add current DC executive credits")
    def add_dc_credits(self, request, queryset) -> None:
        jim = Creator.objects.get(slug="jim-lee")
        marie = Creator.objects.get(slug="marie-javins")
        eic = Role.objects.get(name__iexact="editor in chief")
        pub = Role.objects.get(name__iexact="publisher")
        prez = Role.objects.get(name__iexact="president")
        chief = Role.objects.get(name__iexact="Chief Creative Officer")
        count = 0
        for i in queryset:
            modified = False
            jc, create = Credits.objects.get_or_create(issue=i, creator=jim)
            if create:
                jc.role.add(pub, chief, prez)
                modified = True
            mc, create = Credits.objects.get_or_create(issue=i, creator=marie)
            if create:
                mc.role.add(eic)
                modified = True
            if modified:
                count += 1

        self.message_user(
            request,
            ngettext(
                "%d issue was updated.",
                "%d issues were updated.",
                count,
            )
            % count,
            messages.SUCCESS,
        )

    @admin.action(description="Add current Marvel EIC")
    def add_marvel_credits(self, request, queryset) -> None:
        cb = Creator.objects.get(slug="c-b-cebulski")
        eic = Role.objects.get(name__iexact="editor in chief")
        count = 0
        for i in queryset:
            cred, create = Credits.objects.get_or_create(issue=i, creator=cb)
            if create:
                cred.role.add(eic)
                count += 1

        self.message_user(
            request,
            ngettext(
                "%d issue was updated.",
                "%d issues were updated.",
                count,
            )
            % count,
            messages.SUCCESS,
        )

    @admin.action(description="Add info from reprints")
    def add_reprint_info(self, request, queryset) -> None:
        count = 0
        for i in queryset:
            modified = False
            for reprint in i.reprints.all():
                # If reprint is not a single story let's bail.
                if len(reprint.name) <= MAX_STORIES:
                    modified = True
                    # Add stories
                    if reprint.name:
                        for story in reprint.name:
                            if story not in i.name:
                                i.name.append(story)
                        i.save()
                    # Add characters
                    for character in reprint.characters.all():
                        if character not in i.characters.all():
                            i.characters.add(character)
                    # Add Teams
                    for team in reprint.teams.all():
                        if team not in i.teams.all():
                            i.teams.add(team)
            if modified:
                count += 1

        self.message_user(
            request,
            ngettext(
                "%d Trade Paperback was updated.",
                "%d Trade Paperbacks were updated.",
                count,
            )
            % count,
            messages.SUCCESS,
        )

    @admin.action(description="Add teen rating")
    def add_teen_rating(self, request, queryset) -> None:
        unknown = Rating.objects.get(name="Unknown")
        teen = Rating.objects.get(name="Teen")

        for qs in queryset:
            if qs.rating == unknown:
                qs.rating = teen

        count = Issue.objects.bulk_update(queryset, ["rating"], batch_size=50)

        self.message_user(
            request,
            ngettext("%d issue was updated", "%d issues were updated", count) % count,
            messages.SUCCESS,
        )

from django.contrib import admin, messages
from django.utils.translation import ngettext

from comicsdb.admin.util import CreatedOnDateListFilter
from comicsdb.models import Issue, Series, SeriesType


@admin.register(Series)
class SeriesAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = ("name", "year_began", "created_by")
    list_filter = (CreatedOnDateListFilter, "modified", "series_type", "status", "publisher")
    prepopulated_fields = {"slug": ("name", "year_began")}
    autocomplete_fields = ["associated"]
    actions = ["rename_issue_slugs"]
    actions_on_top = True
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "slug",
                    "sort_name",
                    "publisher",
                    "imprint",
                    "volume",
                    "year_began",
                    "year_end",
                    "series_type",
                    "status",
                    "associated",
                    "desc",
                    "collection",
                    "cv_id",
                    "gcd_id",
                    "edited_by",
                )
            },
        ),
        ("Related", {"fields": ("genres",)}),
    )
    filter_horizontal = ("genres",)

    @admin.action(description="Rename series issues slugs")
    def rename_issue_slugs(self, request, queryset) -> None:
        all_issues_to_update = []
        for qs in queryset:
            issues = list(qs.issues.all())  # Convert queryset to list for efficient appending
            for issue in issues:
                issue.slug = f"{qs.slug}-{issue.number}"
            all_issues_to_update.extend(issues)

        count = Issue.objects.bulk_update(all_issues_to_update, ["slug"])

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


@admin.register(SeriesType)
class SeriesTypeAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    fields = ("name", "notes")

import datetime
from typing import Any, Optional

from django.contrib import admin
from django.db.models.query import QuerySet
from django.forms import ModelForm
from django.forms.widgets import (
    ClearableFileInput,
    DateInput,
    NumberInput,
    Textarea,
    TextInput,
)
from searchableselect.widgets import SearchableSelect
from sorl.thumbnail.admin.current import AdminImageMixin

from comicsdb.forms.credits import CreditsForm
from comicsdb.models import Creator, Credits, Issue, Role, Variant


class FutureStoreDateListFilter(admin.SimpleListFilter):
    title = "future store week"

    parameter_name = "store_date"

    def lookups(self, request: Any, model_admin: Any):
        return (("thisWeek", "This week"), ("nextWeek", "Next week"))

    def queryset(self, request: Any, queryset: QuerySet) -> Optional[QuerySet]:
        today = datetime.date.today()
        year, week, _ = today.isocalendar()

        if self.value() == "thisWeek":
            return queryset.filter(store_date__week=week, store_date__year=year)

        if self.value() == "nextWeek":
            return queryset.filter(store_date__week=week + 1, store_date__year=year)


def add_dc_credits(modeladmin, request, queryset):
    jim = Creator.objects.get(slug="jim-lee")
    marie = Creator.objects.get(slug="marie-javins")
    eic = Role.objects.get(name__iexact="editor in chief")
    pub = Role.objects.get(name__iexact="publisher")
    chief = Role.objects.get(name__iexact="Chief Creative Officer")
    for i in queryset:
        jc, create = Credits.objects.get_or_create(issue=i, creator=jim)
        if create:
            jc.role.add(pub, chief)
        mc, create = Credits.objects.get_or_create(issue=i, creator=marie)
        if create:
            mc.role.add(eic)


add_dc_credits.short_description = "Add current DC executive credits"


def add_marvel_credits(modeladmin, request, queryset):
    cb = Creator.objects.get(slug="c-b-cebulski")
    eic = Role.objects.get(name__iexact="editor in chief")
    for i in queryset:
        cred, create = Credits.objects.get_or_create(issue=i, creator=cb)
        if create:
            cred.role.add(eic)


add_marvel_credits.short_description = "Add current Marvel EIC"


class CreditsInline(admin.TabularInline):
    model = Credits
    form = CreditsForm
    extra = 1


class VariantInline(admin.TabularInline):
    model = Variant
    extra = 1


class IssueAdminForm(ModelForm):
    class Meta:
        model = Issue
        # exclude 'creators' field
        fields = (
            "series",
            "number",
            "slug",
            "name",
            "cover_date",
            "store_date",
            "price",
            "sku",
            "upc",
            "page",
            "desc",
            "characters",
            "teams",
            "arcs",
            "image",
        )
        widgets = {
            "series": SearchableSelect(
                model="comicsdb.Series", search_field="name", many=False, limit=200
            ),
            "number": TextInput(attrs={"class": "input"}),
            "slug": TextInput(attrs={"class": "input"}),
            "name": TextInput(attrs={"class": "input"}),
            "arcs": SearchableSelect(
                model="comicsdb.Arc", search_field="name", many=True, limit=50
            ),
            "characters": SearchableSelect(
                model="comicsdb.Character", search_field="name", many=True, limit=200
            ),
            "teams": SearchableSelect(
                model="comicsdb.Team", search_field="name", many=True, limit=50
            ),
            "cover_date": DateInput(
                attrs={"class": "input", "type": "date"},
            ),
            "store_date": DateInput(
                attrs={"class": "input", "type": "date"},
            ),
            "price": NumberInput(attrs={"class": "input"}),
            "sku": TextInput(attrs={"class": "input"}),
            "upc": TextInput(attrs={"class": "input"}),
            "page": TextInput(attrs={"class": "input"}),
            "desc": Textarea(attrs={"class": "textarea"}),
            "image": ClearableFileInput(),
        }
        help_texts = {
            "name": "Separate multiple story titles by a semicolon",
            "price": "In United States currency",
        }
        labels = {"name": "Story Title"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].delimiter = ";"


@admin.register(Issue)
class IssueAdmin(AdminImageMixin, admin.ModelAdmin):
    form = IssueAdminForm
    search_fields = ("series__name",)
    list_display = ("__str__", "cover_date", "store_date")
    list_filter = (
        FutureStoreDateListFilter,
        "created_on",
        "modified",
        "store_date",
        "cover_date",
        "series__publisher",
    )
    list_select_related = ("series",)
    date_hierarchy = "cover_date"
    actions = [add_dc_credits, add_marvel_credits]
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
                    "cover_date",
                    "store_date",
                    "price",
                    "sku",
                    "upc",
                    "page",
                    "desc",
                    "image",
                    "created_by",
                    "edited_by",
                )
            },
        ),
        ("Related", {"fields": ("characters", "teams", "arcs")}),
    )
    filter_horizontal = ("arcs", "characters", "teams")
    inlines = (CreditsInline, VariantInline)

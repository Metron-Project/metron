"""
Mixins for comicsdb views to reduce code duplication.
"""

import logging
import operator
from functools import reduce

from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.views.generic import RedirectView

from comicsdb.forms.attribution import AttributionFormSet
from comicsdb.models.attribution import Attribution

LOGGER = logging.getLogger(__name__)


class AttributionCreateMixin:
    """
    Mixin for CreateViews that handle attribution formsets.

    Expects the view to have:
    - model attribute set
    - form_class attribute set
    - template_name = "comicsdb/model_with_attribution_form.html"

    Optionally override:
    - title: String for the page title (defaults to "Add {ModelName}")
    - log_message: String for logging (defaults to "{model_name}: %s was created by %s")
    """

    title = None
    log_message = None

    def get_title(self):
        """Get the title for the create page."""
        if self.title:
            return self.title
        return f"Add {self.model.__name__}"

    def get_log_message(self):
        """Get the log message format string."""
        if self.log_message:
            return self.log_message
        return f"{self.model.__name__}: %s was created by %s"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.get_title()
        if self.request.POST:
            context["attribution"] = AttributionFormSet(self.request.POST)
        else:
            context["attribution"] = AttributionFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        attribution_form = context["attribution"]
        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.edited_by = self.request.user
            if attribution_form.is_valid():
                self.object = form.save()
                attribution_form.instance = self.object
                attribution_form.save()
            else:
                return super().form_invalid(form)

        LOGGER.info(self.get_log_message(), form.instance.name, self.request.user)
        return super().form_valid(form)


class AttributionUpdateMixin:
    """
    Mixin for UpdateViews that handle attribution formsets.

    Expects the view to have:
    - model attribute set
    - form_class attribute set
    - template_name = "comicsdb/model_with_attribution_form.html"
    - attribution_field: Name of the field in Attribution model (e.g., "arcs", "characters")

    Optionally override:
    - get_title(): Method that returns title string
    - log_message: String for logging (defaults to "{model_name}: %s was updated by %s")
    """

    attribution_field = None
    log_message = None

    def get_title(self):
        """
        Get the title for the update page.
        Override this method to customize the title.
        """
        obj = self.object
        return f"Edit information for {obj}"

    def get_log_message(self):
        """Get the log message format string."""
        if self.log_message:
            return self.log_message
        return f"{self.model.__name__}: %s was updated by %s"

    def get_attribution_queryset(self):
        """Get the queryset for existing attributions."""
        if not self.attribution_field:
            raise NotImplementedError(
                f"{self.__class__.__name__} must define 'attribution_field' attribute"
            )
        filter_kwargs = {self.attribution_field: self.object}
        return Attribution.objects.filter(**filter_kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.get_title()
        if self.request.POST:
            context["attribution"] = AttributionFormSet(
                self.request.POST,
                instance=self.object,
                queryset=self.get_attribution_queryset(),
                prefix="attribution",
            )
            context["attribution"].full_clean()
        else:
            context["attribution"] = AttributionFormSet(
                instance=self.object,
                queryset=self.get_attribution_queryset(),
                prefix="attribution",
            )
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        attribution_form = context["attribution"]
        with transaction.atomic():
            form.instance.edited_by = self.request.user
            if attribution_form.is_valid():
                self.object = form.save(commit=False)
                attribution_form.instance = self.object
                attribution_form.save()
            else:
                return super().form_invalid(form)

        LOGGER.info(self.get_log_message(), form.instance.name, self.request.user)
        return super().form_valid(form)


class NavigationMixin:
    """
    Mixin for DetailViews that adds next/previous navigation.

    Adds a "navigation" dict to context with next_{model} and previous_{model} keys.
    Override get_navigation_queryset() to customize the base queryset.
    Override get_ordering_field() to change the field used for ordering (default: "name").
    """

    def get_ordering_field(self):
        """Get the field name used for ordering. Default is 'name'."""
        return "name"

    def get_navigation_queryset(self):
        """Get the base queryset for navigation. Default is all objects."""
        return self.model.objects.all()

    def get_navigation_context(self):
        """Get the navigation context dict."""
        obj = self.get_object()
        ordering_field = self.get_ordering_field()
        qs = self.get_navigation_queryset().order_by(ordering_field)

        # Build filter kwargs dynamically
        gt_filter = {f"{ordering_field}__gt": getattr(obj, ordering_field)}
        lt_filter = {f"{ordering_field}__lt": getattr(obj, ordering_field)}

        next_obj = qs.filter(**gt_filter).first()
        previous_obj = qs.filter(**lt_filter).last()

        model_name = self.model.__name__.lower()
        return {
            f"next_{model_name}": next_obj,
            f"previous_{model_name}": previous_obj,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["navigation"] = self.get_navigation_context()
        return context


class SearchMixin:
    """
    Mixin for ListView that adds search functionality.

    Searches for query parameter 'q' in GET request.
    Override get_search_fields() to specify which fields to search.
    Override get_search_operator() to change AND/OR logic (default: AND).
    """

    def get_search_fields(self):
        """
        Return a list of field lookups to search.
        Example: ["name__icontains", "alias__icontains"]
        """
        return ["name__icontains"]

    def get_search_operator(self):
        """Get the operator to combine search terms. Default is operator.and_"""
        return operator.and_

    def get_search_queryset(self, queryset, query):
        """Apply search filters to the queryset."""
        query_list = query.split()
        search_fields = self.get_search_fields()
        operator_func = self.get_search_operator()

        # Build Q objects for each query term across all search fields
        q_objects = []
        for q_term in query_list:
            # For each term, create Q objects for all search fields (OR together)
            field_q_objects = [Q(**{field: q_term}) for field in search_fields]
            # Combine field Q objects with OR
            if len(field_q_objects) > 1:
                combined_field_q = reduce(lambda a, b: a | b, field_q_objects)
            else:
                combined_field_q = field_q_objects[0]
            q_objects.append(combined_field_q)

        # Combine term Q objects with the specified operator (AND by default)
        if q_objects:
            final_q = reduce(operator_func, q_objects)
            return queryset.filter(final_q)

        return queryset

    def get_queryset(self):
        result = super().get_queryset()
        if query := self.request.GET.get("q"):
            result = self.get_search_queryset(result, query)
        return result


class SlugRedirectView(RedirectView):
    """
    Generic redirect view that redirects from pk-based URL to slug-based URL.

    Set the model and url_name attributes on the subclass.

    Example:
        class ArcDetailRedirect(SlugRedirectView):
            model = Arc
            url_name = "arc:detail"
    """

    model = None
    url_name = None

    def get_redirect_url(self, pk):
        if not self.model:
            raise NotImplementedError(f"{self.__class__.__name__} must define 'model' attribute")
        if not self.url_name:
            raise NotImplementedError(f"{self.__class__.__name__} must define 'url_name' attribute")
        obj = self.model.objects.get(pk=pk)
        return reverse(self.url_name, kwargs={"slug": obj.slug})

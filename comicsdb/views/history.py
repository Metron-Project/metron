from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView


class HistoryListView(LoginRequiredMixin, ListView):
    """Generic view to display edit history for models with django-simple-history."""

    template_name = "comicsdb/history_list.html"
    paginate_by = 25
    context_object_name = "history_list"

    def setup(self, request, *args, **kwargs):
        """Initialize attributes shared by all view methods."""
        super().setup(request, *args, **kwargs)
        # Cache the object to avoid duplicate queries
        self.obj = self.model.objects.get(slug=self.kwargs["slug"])

    def get_queryset(self):
        """Get the history for the object with optimized queries."""
        # Use select_related to avoid N+1 queries on history_user
        return self.obj.history.select_related("history_user").all()

    def get_context_data(self, **kwargs):
        """
        Add the object and delta information to the context.
        Computing deltas only for the current page is more efficient.
        """
        context = super().get_context_data(**kwargs)
        context["object"] = self.obj
        context["model_name"] = self.model._meta.verbose_name

        # Add delta information for each record on the current page
        history_list = list(context["history_list"])

        # Get the next record (if exists) for the last item on the page
        page_obj = context.get("page_obj")
        if page_obj and page_obj.has_next() and history_list:
            try:
                # Get one more record after the page for delta calculation
                queryset = self.get_queryset()
                last_index = page_obj.number * self.paginate_by
                next_record = queryset[last_index] if last_index < queryset.count() else None
            except (IndexError, AttributeError):
                next_record = None
        else:
            next_record = None

        # Compute deltas for this page
        for i, record in enumerate(history_list):
            if i < len(history_list) - 1:
                # Compare with the next record in the list (previous in time)
                record.delta = record.diff_against(history_list[i + 1])
            elif next_record:
                # For the last record on page, compare with first of next page
                record.delta = record.diff_against(next_record)
            else:
                record.delta = None

        # Update the context with the modified list
        context["history_list"] = history_list

        return context

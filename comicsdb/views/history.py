from dataclasses import replace

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
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

    def _resolve_m2m_value(self, field_name, value):  # noqa: PLR0911, PLR0912
        """
        Convert many-to-many field IDs to their string representations.

        Args:
            field_name: The name of the field
            value: The value (could be a list of dicts with IDs, or other formats)

        Returns:
            A formatted string with object names instead of IDs
        """
        # Get the field from the model
        if not self.model:
            return value

        try:
            field = self.model._meta.get_field(field_name)
        except Exception:  # noqa: BLE001
            # If we can't get the field, return the original value
            return value

        # Check if it's a ManyToManyField
        if not isinstance(field, models.ManyToManyField):
            return value

        # If the value is None or empty, return as-is
        if not value:
            return value

        # Extract IDs from the M2M value
        # django-simple-history stores M2M as list of dicts like [{'field1': id1, 'field2': id2}]
        ids = []
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    # Find the key that corresponds to the related model's ID
                    # It's usually the field name without the '_id' suffix
                    related_field_name = field_name.rstrip("s")  # Simple pluralization removal
                    if related_field_name in item:
                        ids.append(item[related_field_name])
                elif isinstance(item, int):
                    # Sometimes it might just be a list of IDs
                    ids.append(item)
        elif isinstance(value, str):
            # Handle string representations
            return value
        else:
            return value

        if not ids:
            return value

        # Get the related model and fetch the objects
        related_model = field.related_model

        try:
            objects = related_model.objects.filter(id__in=ids)
            # Create a mapping of ID to name for proper ordering
            id_to_name = {obj.id: str(obj) for obj in objects}
            # Maintain the order from the original IDs list
            names = [id_to_name.get(id_, f"ID:{id_}") for id_ in ids if id_ in id_to_name]
            return ", ".join(names) if names else value
        except Exception:  # noqa: BLE001
            # If anything goes wrong, return the original value
            return value

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

            # Process delta to convert M2M IDs to names
            # Since the change objects are frozen dataclasses, we need to replace them
            if record.delta and record.delta.changes:
                new_changes = []
                for change in record.delta.changes:
                    # Resolve old and new values for M2M fields
                    resolved_old = self._resolve_m2m_value(change.field, change.old)
                    resolved_new = self._resolve_m2m_value(change.field, change.new)

                    # Only create a new change if values were modified
                    if resolved_old != change.old or resolved_new != change.new:
                        new_change = replace(change, old=resolved_old, new=resolved_new)
                        new_changes.append(new_change)
                    else:
                        new_changes.append(change)

                # Replace the entire delta object with updated changes
                record.delta = replace(record.delta, changes=new_changes)

        # Update the context with the modified list
        context["history_list"] = history_list

        return context

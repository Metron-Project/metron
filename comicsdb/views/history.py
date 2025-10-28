from collections import defaultdict
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

    def _extract_m2m_ids(self, field_name, value):
        """
        Extract IDs from M2M field value.

        Args:
            field_name: The name of the field
            value: The value (could be a list of dicts with IDs, or other formats)

        Returns:
            List of IDs or None if not applicable
        """
        if not value or not isinstance(value, list):
            return None

        ids = []
        for item in value:
            if isinstance(item, dict):
                # Find the key that corresponds to the related model's ID
                related_field_name = field_name.rstrip("s")  # Simple pluralization removal
                if related_field_name in item:
                    ids.append(item[related_field_name])
            elif isinstance(item, int):
                ids.append(item)

        return ids if ids else None

    def _prefetch_m2m_names(self, history_list):
        """
        Prefetch all M2M object names in a single query per model to avoid N+1 queries.

        Args:
            history_list: List of history records with delta information

        Returns:
            Dict mapping (model_class, field_name) -> {id: name}
        """
        # Collect all M2M field IDs that need to be resolved
        m2m_ids_by_field = defaultdict(set)

        for record in history_list:
            if not record.delta or not record.delta.changes:
                continue

            for change in record.delta.changes:
                try:
                    field = self.model._meta.get_field(change.field)
                except Exception:  # noqa: BLE001 S112
                    continue

                if not isinstance(field, models.ManyToManyField):
                    continue

                # Extract IDs from old and new values
                for value in [change.old, change.new]:
                    ids = self._extract_m2m_ids(change.field, value)
                    if ids:
                        m2m_ids_by_field[(field.related_model, change.field)].update(ids)

        # Batch fetch all related objects
        m2m_cache = {}
        for (related_model, field_name), ids in m2m_ids_by_field.items():
            try:
                objects = related_model.objects.filter(id__in=ids)
                m2m_cache[(related_model, field_name)] = {obj.id: str(obj) for obj in objects}
            except Exception:  # noqa: BLE001
                m2m_cache[(related_model, field_name)] = {}

        return m2m_cache

    def _resolve_m2m_value(self, field_name, value, m2m_cache):  # noqa: PLR0911
        """
        Convert many-to-many field IDs to their string representations using cache.

        Args:
            field_name: The name of the field
            value: The value (could be a list of dicts with IDs, or other formats)
            m2m_cache: Prefetched cache of M2M object names

        Returns:
            A formatted string with object names instead of IDs
        """
        # Get the field from the model
        if not self.model:
            return value

        try:
            field = self.model._meta.get_field(field_name)
        except Exception:  # noqa: BLE001
            return value

        # Check if it's a ManyToManyField
        if not isinstance(field, models.ManyToManyField):
            return value

        # If the value is None or empty, return as-is
        if not value:
            return value

        # Extract IDs
        ids = self._extract_m2m_ids(field_name, value)
        if not ids:
            if isinstance(value, str):
                return value
            return value

        # Get the cached names
        related_model = field.related_model
        cache_key = (related_model, field_name)
        id_to_name = m2m_cache.get(cache_key, {})

        # Maintain the order from the original IDs list
        names = [id_to_name.get(id_, f"ID:{id_}") for id_ in ids if id_ in id_to_name]
        return ", ".join(names) if names else value

    def get_context_data(self, **kwargs):  # noqa: PLR0912
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
                # Use list slicing to avoid expensive count() query
                queryset = self.get_queryset()
                last_index = page_obj.number * self.paginate_by
                try:
                    next_record = queryset[last_index]
                except IndexError:
                    next_record = None
            except AttributeError:
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

        # Prefetch all M2M names in batch to avoid N+1 queries
        m2m_cache = self._prefetch_m2m_names(history_list)

        # Process delta to convert M2M IDs to names
        for record in history_list:
            if record.delta and record.delta.changes:
                new_changes = []
                for change in record.delta.changes:
                    # Resolve old and new values for M2M fields using cache
                    resolved_old = self._resolve_m2m_value(change.field, change.old, m2m_cache)
                    resolved_new = self._resolve_m2m_value(change.field, change.new, m2m_cache)

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

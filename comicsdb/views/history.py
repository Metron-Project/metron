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

    def _get_field(self, field_name, field_class):
        """Return the model field ``field_name`` if it is a ``field_class``, else ``None``."""
        if not self.model:
            return None
        try:
            field = self.model._meta.get_field(field_name)
        except Exception:  # noqa: BLE001
            return None
        return field if isinstance(field, field_class) else None

    @staticmethod
    def _fk_ids(_field_name, value):
        """Return the FK id in ``value`` as a list, or ``None``."""
        return [value] if isinstance(value, int) else None

    def _prefetch_related_names(self, history_list, field_class, extract_ids):
        """
        Fetch the names of related objects referenced by the deltas, one query per model.

        Args:
            history_list: List of history records with delta information
            field_class: ``models.ForeignKey`` or ``models.ManyToManyField``
            extract_ids: ``(field_name, value) -> list of ids | None``

        Returns:
            Dict mapping (model_class, field_name) -> {id: name}
        """
        ids_by_field = defaultdict(set)
        for record in history_list:
            if not record.delta or not record.delta.changes:
                continue
            for change in record.delta.changes:
                field = self._get_field(change.field, field_class)
                if field is None:
                    continue
                for value in (change.old, change.new):
                    if ids := extract_ids(change.field, value):
                        ids_by_field[(field.related_model, change.field)].update(ids)

        cache = {}
        for (related_model, field_name), ids in ids_by_field.items():
            try:
                objects = related_model.objects.filter(id__in=ids)
                cache[(related_model, field_name)] = {obj.id: str(obj) for obj in objects}
            except Exception:  # noqa: BLE001
                cache[(related_model, field_name)] = {}
        return cache

    def _prefetch_fk_names(self, history_list):
        """Map (model_class, field_name) -> {id: name} for ForeignKey ids in the deltas."""
        return self._prefetch_related_names(history_list, models.ForeignKey, self._fk_ids)

    def _prefetch_m2m_names(self, history_list):
        """Map (model_class, field_name) -> {id: name} for many-to-many ids in the deltas."""
        return self._prefetch_related_names(
            history_list, models.ManyToManyField, self._extract_m2m_ids
        )

    def _resolve_m2m_value(self, field_name, value, m2m_cache):
        """
        Convert many-to-many field IDs to their string representations using cache.

        Args:
            field_name: The name of the field
            value: The value (could be a list of dicts with IDs, or other formats)
            m2m_cache: Prefetched cache of M2M object names

        Returns:
            A formatted string with object names instead of IDs, or the original
            value if it can't be resolved
        """
        field = self._get_field(field_name, models.ManyToManyField)
        ids = self._extract_m2m_ids(field_name, value) if field is not None else None
        if not ids:
            return value

        # Maintain the order from the original IDs list
        id_to_name = m2m_cache.get((field.related_model, field_name), {})
        names = [id_to_name[id_] for id_ in ids if id_ in id_to_name]
        return ", ".join(names) if names else value

    def _resolve_fk_value(self, field_name, value, fk_cache):
        """
        Convert foreign key field ID to its string representation using cache.

        Args:
            field_name: The name of the field
            value: The value (should be an integer ID)
            fk_cache: Prefetched cache of FK object names

        Returns:
            The object name string or the original value if not resolvable
        """
        field = self._get_field(field_name, models.ForeignKey)
        if field is None or not isinstance(value, int):
            return value
        return fk_cache.get((field.related_model, field_name), {}).get(value, value)

    def _get_next_record(self, page_obj, history_list):
        """Return the record just after this page (to diff the page's last record against)."""
        if not (page_obj and page_obj.has_next() and history_list):
            return None
        # Index instead of paginating again, to avoid an expensive count() query.
        try:
            return self.get_queryset()[page_obj.number * self.paginate_by]
        except IndexError, AttributeError:
            return None

    @staticmethod
    def _attach_deltas(history_list, next_record):
        """Set ``record.delta`` to the diff against the previous (older) record.

        The page's last record is diffed against ``next_record`` (the first record
        of the next page), or gets no delta if there isn't one.
        """
        for i, record in enumerate(history_list):
            older = history_list[i + 1] if i + 1 < len(history_list) else next_record
            record.delta = record.diff_against(older) if older else None

    def _resolve_change(self, change, fk_cache, m2m_cache):
        """Return ``change`` with FK and M2M ids in old/new replaced by object names."""
        resolved_old = self._resolve_fk_value(change.field, change.old, fk_cache)
        resolved_new = self._resolve_fk_value(change.field, change.new, fk_cache)
        resolved_old = self._resolve_m2m_value(change.field, resolved_old, m2m_cache)
        resolved_new = self._resolve_m2m_value(change.field, resolved_new, m2m_cache)
        if resolved_old == change.old and resolved_new == change.new:
            return change
        return replace(change, old=resolved_old, new=resolved_new)

    def get_context_data(self, **kwargs):
        """
        Add the object and delta information to the context.
        Computing deltas only for the current page is more efficient.
        """
        context = super().get_context_data(**kwargs)
        context["object"] = self.obj
        context["model_name"] = self.model._meta.verbose_name

        history_list = list(context["history_list"])
        next_record = self._get_next_record(context.get("page_obj"), history_list)
        self._attach_deltas(history_list, next_record)

        # Prefetch all FK and M2M names in batch to avoid N+1 queries
        fk_cache = self._prefetch_fk_names(history_list)
        m2m_cache = self._prefetch_m2m_names(history_list)
        for record in history_list:
            if record.delta and record.delta.changes:
                changes = [
                    self._resolve_change(change, fk_cache, m2m_cache)
                    for change in record.delta.changes
                ]
                record.delta = replace(record.delta, changes=changes)

        context["history_list"] = history_list
        return context

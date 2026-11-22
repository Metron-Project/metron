"""Shared mixins and base classes for the v1.0 API viewsets: response caching,
user tracking and per-action serializer selection."""

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.http import Http404
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_condition import last_modified

from api.cache import DETAIL_CACHE_TTL, LIST_CACHE_TTL, detail_cache_key, list_cache_key
from api.v1_0.serializers import IssueListSerializer


def mark_cache_status(response: Response, *, hit: bool) -> Response:
    """Tag a response with whether it came from the Redis response cache,
    so cache behavior can be checked in production with `curl -I` instead
    of inspecting Redis directly. Only called on the paths that actually
    went through a cache.get()/cache.set() -- a viewset/action with caching
    disabled (no cache_model_label) gets no header at all, rather than a
    misleading MISS."""
    response["X-Cache"] = "HIT" if hit else "MISS"
    return response


class CachedObjectMixin:
    #: Set on concrete viewsets to enable response caching; None disables it
    #: (fail-open -- behaves exactly as before this attribute existed).
    cache_model_label: str | None = None

    def get_object(self):
        if not hasattr(self, "_cached_object"):
            self._cached_object = super().get_object()

        return self._cached_object

    def get_modified_queryset(self):
        """Queryset used by get_object_modified() for its (pk, modified)
        lookup. Defaults to get_queryset(), but a viewset whose
        get_queryset() adds annotate() aggregates should override this to
        return a lean, unannotated queryset with the same row-level
        permission scoping -- an annotated aggregate still forces a JOIN +
        GROUP BY even when values_list() doesn't select the annotated
        field.
        """
        return self.get_queryset()

    def get_object_modified(self):
        """Cheap (pk, modified) lookup for conditional-request checks and
        cache-key computation -- does NOT trigger the full get_object()
        queryset (select_related/prefetch_related/annotate). That heavier
        query only runs lazily if get_object() is later called for an
        actual cache-miss render.
        """
        if not hasattr(self, "_cached_object_modified"):
            if hasattr(self, "_cached_object"):
                # get_object() already ran this request -- reuse it instead
                # of doing a second query.
                obj = self._cached_object
                self._cached_object_modified = (
                    getattr(obj, "pk", None),
                    getattr(obj, "modified", None),
                )
            else:
                lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
                pk = self.kwargs[lookup_url_kwarg]
                # get_modified_queryset()/filter_queryset(), not a bare
                # Model.objects, so this still respects per-viewset row
                # scoping (e.g. CollectionViewSet/PullListViewSet/
                # WishListViewSet filtering by user).
                try:
                    row = (
                        self.filter_queryset(self.get_modified_queryset())
                        .filter(**{self.lookup_field: pk})
                        .values_list(self.lookup_field, "modified")
                        .first()
                    )
                except ValueError, TypeError, ValidationError:
                    # Mirrors get_object_or_404()'s handling of a lookup value
                    # that can't be coerced to the field's type (e.g. a
                    # non-numeric value against an integer pk) -- treat it as
                    # "not found" rather than a 500, and let get_object()'s
                    # own get_object_or_404() raise the real Http404 below.
                    row = None
                self._cached_object_modified = row if row else (None, None)

        return self._cached_object_modified


class ConditionalRetrieveModelMixin(CachedObjectMixin, mixins.RetrieveModelMixin):
    #: Other models' cache-generation counters (see api/cache.py) to mix
    #: into the detail cache key, for responses that embed a related
    #: object's fields where an edit to that related object doesn't cascade
    #: a `modified` bump onto this one.
    cache_detail_dependent_labels: tuple[str, ...] = ()

    def retrieve(self, request, *args, **kwargs):
        # _cached_retrieve must be passed unbound: rest_framework_condition's
        # condition() re-supplies `self` itself (it's built to decorate a
        # plain function via Python's descriptor protocol). Passing an
        # already-bound method here double-supplies `self`, silently
        # rebinding _cached_retrieve's `request` param to the ViewSet
        # instance instead of the real DRF request.
        retrieve = last_modified(last_modified_func=self._retrieve_last_modified)(
            type(self)._cached_retrieve
        )

        return retrieve(self, request, *args, **kwargs)

    def _retrieve_last_modified(self, *args, **kwargs):
        _pk, modified = self.get_object_modified()

        return modified

    def _cached_retrieve(self, request, *args, **kwargs):
        """Reached only once rest_framework_condition's last_modified() has
        already ruled out a 304 -- i.e. exactly where a cache lookup is
        worth doing.

        Note: a cache hit returns without calling get_object(), so
        check_object_permissions() never runs on that path. Every
        permission class in this project is view-level only (none override
        has_object_permission), so this is currently inert -- but a future
        object-level permission class on a cache_model_label-enabled
        viewset would need get_object_modified() (or this method) to also
        enforce it explicitly, since DRF's default only calls it from
        get_object().
        """
        pk, modified = self.get_object_modified()
        if not self.cache_model_label or modified is None:
            return mixins.RetrieveModelMixin.retrieve(self, request, *args, **kwargs)

        key = detail_cache_key(
            self.cache_model_label,
            "retrieve",
            pk,
            modified,
            *self.cache_detail_dependent_labels,
            request=self.request,
        )
        cached = cache.get(key)
        if cached is not None:
            return mark_cache_status(Response(cached), hit=True)

        response = mixins.RetrieveModelMixin.retrieve(self, request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            cache.set(key, response.data, DETAIL_CACHE_TTL)
        return mark_cache_status(response, hit=False)


class UserTrackingMixin:
    """Mixin to automatically track user edits in create and update operations."""

    def perform_create(self, serializer):
        serializer.save(edited_by=self.request.user, created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(edited_by=self.request.user)


class CachedListModelMixin(mixins.ListModelMixin):
    """Drop-in replacement for mixins.ListModelMixin that caches list()
    responses under a per-model cache-generation counter (see api/cache.py).
    """

    cache_model_label: str | None = None
    cache_dependent_labels: tuple[str, ...] = ()
    #: Query params whose (non-empty) presence bypasses the cache, for
    #: lookups whose values are nearly always unique (e.g. a scanned cover's
    #: phash), where caching would only fill Redis with entries never re-read.
    uncached_list_params: tuple[str, ...] = ()

    def list(self, request, *args, **kwargs):
        if not self.cache_model_label or any(
            # Strip to match the filter form's cleaned value, so whitespace-only
            # input (which the filter ignores) is cached like the plain list.
            request.query_params.get(param, "").strip()
            for param in self.uncached_list_params
        ):
            return super().list(request, *args, **kwargs)

        key = list_cache_key(
            self.cache_model_label,
            *self.cache_dependent_labels,
            request=request,
        )
        cached = cache.get(key)
        if cached is not None:
            return mark_cache_status(Response(cached), hit=True)

        response = super().list(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            cache.set(key, response.data, LIST_CACHE_TTL)
        return mark_cache_status(response, hit=False)


class CachedDetailActionMixin(CachedObjectMixin):
    """Shared cache-wrapping logic for detail-scoped list actions
    (issue_list, etc.) that paginate a related queryset off a parent object.
    Cached under the parent's own `modified` timestamp, since that already
    captures "has this parent's related collection changed" via the
    existing modified-cascade signals.
    """

    #: Other models' cache-generation counters (see api/cache.py) to mix
    #: into the action's cache key, for actions whose payload can change
    #: without the parent object's own `modified` being touched (e.g.
    #: issue_list embeds fields from Issue rows that don't cascade a
    #: `modified` bump onto the parent Arc/Character/Team on every edit --
    #: only on M2M add/remove/clear).
    #:
    #: ModelLabel.ISSUE/SERIES are deliberately NOT used here by any
    #: issue_list viewset: both are bumped by
    #: update_series_modified_on_issue_save() on *every* issue write anywhere
    #: on the site, so tying this 24h-TTL cache to either would invalidate
    #: every parent's issue_list on essentially any issue edit site-wide --
    #: confirmed as a live problem for IssueViewSet's own retrieve cache in
    #: production (see its cache_detail_dependent_labels comment). A plain
    #: issue field edit can show stale in issue_list for up to
    #: DETAIL_CACHE_TTL; that's the accepted tradeoff.
    cache_action_dependent_labels: tuple[str, ...] = ()

    def _cached_paginated_action(self, *, build_queryset, serializer_class):
        pk, modified = self.get_object_modified()
        key = None
        if self.cache_model_label and modified is not None:
            key = detail_cache_key(
                self.cache_model_label,
                self.action,
                pk,
                modified,
                *self.cache_action_dependent_labels,
                request=self.request,
            )
            cached = cache.get(key)
            if cached is not None:
                return mark_cache_status(Response(cached), hit=True)

        obj = self.get_object()
        queryset = build_queryset(obj)
        page = self.paginate_queryset(queryset)
        if page is None:
            raise Http404
        serializer = serializer_class(page, many=True, context={"request": self.request})
        response = self.get_paginated_response(serializer.data)
        if key is not None:
            cache.set(key, response.data, DETAIL_CACHE_TTL)
            response = mark_cache_status(response, hit=False)
        return response


class IssueListMixin(CachedDetailActionMixin):
    """Mixin to provide a standard issue_list action for related models."""

    def get_issue_queryset(self, obj):
        """Override to customize the issue queryset for a specific viewset."""
        return obj.issues.select_related("series", "series__series_type").order_by(
            "cover_date", "series", "number"
        )

    @extend_schema(responses={200: IssueListSerializer(many=True)}, filters=False)
    @action(detail=True)
    def issue_list(self, request, *args, **kwargs):
        # See the comment in ConditionalRetrieveModelMixin.retrieve: _issue_list
        # must be passed unbound for the same reason.
        issue_list = last_modified(last_modified_func=self._issue_list_last_modified)(
            type(self)._issue_list
        )

        return issue_list(self, request, *args, **kwargs)

    def _issue_list(self, request, *args, **kwargs):
        """Returns a list of issues for this object."""
        return self._cached_paginated_action(
            build_queryset=self.get_issue_queryset,
            serializer_class=IssueListSerializer,
        )

    def _issue_list_last_modified(self, *args, **kwargs):
        _pk, modified = self.get_object_modified()

        return modified


# The two classes below deliberately use comments instead of docstrings:
# drf-spectacular falls back to an inherited class docstring as the operation
# description, so a docstring here would leak into the OpenAPI schema of any
# viewset that has no docstring of its own.


# Choose the serializer by action from ``serializer_classes``; actions missing
# from the mapping fall back to ``serializer_class``.
class ActionSerializerMixin:
    serializer_classes: dict = {}

    def get_serializer_class(self):
        if self.action in self.serializer_classes:
            return self.serializer_classes[self.action]
        return super().get_serializer_class()


# Base for the catalog resources (arc, character, issue, series, ...): cached
# list/retrieve, plus create/update that record ``created_by``/``edited_by``.
# Combine with ``IssueListMixin`` for an ``issue_list`` action.
class CatalogViewSet(
    ActionSerializerMixin,
    UserTrackingMixin,
    mixins.CreateModelMixin,
    ConditionalRetrieveModelMixin,
    CachedListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    pass

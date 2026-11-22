"""Mixins for views that act on one reading list from the URL slug."""

from django.shortcuts import get_object_or_404
from django.urls import reverse

from reading_lists.models import ReadingList
from reading_lists.services import can_manage_reading_list


class ReadingListFromSlugMixin:
    """Fetch the parent ReadingList named by the ``slug`` URL kwarg into ``self.reading_list``.

    Must precede auth mixins (``LoginRequiredMixin``, ``UserPassesTestMixin``) in the
    base class list so ``self.reading_list`` is set before ``UserPassesTestMixin``
    calls ``test_func()``.
    """

    def get_reading_list_queryset(self):
        return ReadingList.objects.all()

    def dispatch(self, request, *args, **kwargs):
        self.reading_list = get_object_or_404(self.get_reading_list_queryset(), slug=kwargs["slug"])
        return super().dispatch(request, *args, **kwargs)


class ManageReadingListMixin(ReadingListFromSlugMixin):
    """Restrict access to users who can manage ``self.reading_list``, and expose it."""

    def test_func(self):
        return can_manage_reading_list(self.request.user, self.reading_list)

    def get_success_url(self):
        return reverse("reading-list:detail", kwargs={"slug": self.reading_list.slug})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["reading_list"] = self.reading_list
        return context

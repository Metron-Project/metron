"""Create, update, delete and assign-to-Metron views for reading lists."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import CreateView, DeleteView, UpdateView

from reading_lists.forms import ReadingListForm
from reading_lists.models import ReadingList
from reading_lists.services import can_assign_reading_list_to_metron, can_manage_reading_list
from reading_lists.views.mixins import ReadingListFromSlugMixin
from users.models import CustomUser


class ReadingListCreateView(LoginRequiredMixin, CreateView):
    """Create a new reading list."""

    model = ReadingList
    form_class = ReadingListForm
    template_name = "reading_lists/readinglist_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_form(self, form_class=None):
        """Customize form to exclude attribution fields for non-admin users."""
        form = super().get_form(form_class)
        if not self.request.user.is_staff:
            # Remove attribution fields for non-admin users
            form.fields.pop("attribution_source", None)
            form.fields.pop("attribution_url", None)
        return form

    def form_valid(self, form):
        # Set the user to the current user
        form.instance.user = self.request.user
        messages.success(
            self.request, _("Reading list '%(name)s' created!") % {"name": form.instance.name}
        )
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Create Reading List")
        context["button_text"] = _("Create")
        return context


class ReadingListUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Update an existing reading list."""

    model = ReadingList
    form_class = ReadingListForm
    template_name = "reading_lists/readinglist_form.html"

    def test_func(self):
        """Only allow authorized users to edit the list."""
        reading_list = self.get_object()
        return can_manage_reading_list(self.request.user, reading_list)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_form(self, form_class=None):
        """Customize form to exclude attribution fields for non-admin users."""
        form = super().get_form(form_class)
        if not self.request.user.is_staff:
            # Remove attribution fields for non-admin users
            form.fields.pop("attribution_source", None)
            form.fields.pop("attribution_url", None)
        return form

    def form_valid(self, form):
        # Update the edited_by field (via the modified timestamp)
        messages.success(
            self.request, _("Reading list '%(name)s' updated!") % {"name": form.instance.name}
        )
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Edit Reading List")
        context["button_text"] = _("Update")
        return context


class ReadingListDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Delete a reading list."""

    model = ReadingList
    template_name = "reading_lists/readinglist_confirm_delete.html"
    success_url = reverse_lazy("reading-list:my-lists")

    def test_func(self):
        """Only allow authorized users to delete the list."""
        reading_list = self.get_object()
        return can_manage_reading_list(self.request.user, reading_list)

    def form_valid(self, form):
        messages.success(
            self.request, _("Reading list '%(name)s' deleted!") % {"name": self.object.name}
        )
        return super().form_valid(form)


class AssignReadingListToMetronView(
    ReadingListFromSlugMixin, LoginRequiredMixin, UserPassesTestMixin, View
):
    """Reassign a reading list's owner to the Metron account."""

    def get_reading_list_queryset(self):
        # Only lists the editor can already see: another user's private list is a 404,
        # so it can't be taken over (or its slug confirmed) by guessing its slug.
        return ReadingList.objects.visible_to(self.request.user)

    def test_func(self):
        """Only allow staff or 'reading list editor' group members."""
        return can_assign_reading_list_to_metron(self.request.user)

    def get(self, request, *args, **kwargs):
        if self.reading_list.user.username == "Metron":
            return redirect(self.reading_list.get_absolute_url())
        return render(
            request,
            "reading_lists/readinglist_confirm_assign_metron.html",
            {"reading_list": self.reading_list},
        )

    def post(self, request, *args, **kwargs):
        try:
            metron_user = CustomUser.objects.get(username="Metron")
        except CustomUser.DoesNotExist:
            messages.error(request, _("The 'Metron' user account does not exist."))
            return redirect(self.reading_list.get_absolute_url())

        if self.reading_list.user_id != metron_user.id:
            self.reading_list.user = metron_user
            self.reading_list.save()
            messages.success(
                request,
                _("Ownership of '%(name)s' has been reassigned to Metron.")
                % {"name": self.reading_list.name},
            )
        return redirect(self.reading_list.get_absolute_url())

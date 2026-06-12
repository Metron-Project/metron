from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import DeleteView, FormView, UpdateView

from comicsdb.models.issue import Issue
from user_collection.models import CollectionItem
from wish_list.forms import AcquireWishListItemForm, WishListItemForm
from wish_list.models import WishList, WishListItem


def get_or_create_wish_list(user):
    wish_list, _ = WishList.objects.get_or_create(user=user)
    return wish_list


class WishListDetailView(LoginRequiredMixin, FormView):
    template_name = "wish_list/wishlist_detail.html"
    form_class = WishListItemForm

    def get_wish_list(self):
        if not hasattr(self, "_wish_list"):
            self._wish_list = get_or_create_wish_list(self.request.user)
        return self._wish_list

    def form_valid(self, form):
        wish_list = self.get_wish_list()
        issue = form.cleaned_data["issue"]
        if WishListItem.objects.filter(wish_list=wish_list, issue=issue).exists():
            messages.info(self.request, f"{issue} is already on your wish list.")
            return redirect(self.get_success_url())
        item = form.save(commit=False)
        item.wish_list = wish_list
        item.save()
        messages.success(self.request, f"Added {issue} to your wish list.")
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("wish-list:detail")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        wish_list = self.get_wish_list()
        context["wish_list"] = wish_list
        context["wish_list_items"] = wish_list.wish_list_items.select_related(
            "issue__series__series_type",
            "issue__series__publisher",
        ).order_by("priority", "issue__series__sort_name", "issue__cover_date")
        context["is_owner"] = True
        return context


class WishListItemUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = WishListItem
    form_class = WishListItemForm
    template_name = "wish_list/wishlist_item_form.html"
    success_url = reverse_lazy("wish-list:detail")

    def test_func(self):
        return self.get_object().wish_list.user == self.request.user

    def form_valid(self, form):
        messages.success(self.request, f"Updated {self.object.issue}.")
        return super().form_valid(form)


class WishListItemDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = WishListItem
    template_name = "wish_list/wishlist_item_confirm_delete.html"
    success_url = reverse_lazy("wish-list:detail")

    def test_func(self):
        return self.get_object().wish_list.user == self.request.user

    def form_valid(self, form):
        messages.success(self.request, f"Removed {self.object.issue} from your wish list.")
        return super().form_valid(form)


class AcquireWishListItemView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    form_class = AcquireWishListItemForm
    template_name = "wish_list/wishlist_acquire_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.wish_list_item = get_object_or_404(WishListItem, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def test_func(self):
        return self.wish_list_item.wish_list.user == self.request.user

    def form_valid(self, form):
        item = self.wish_list_item
        _, created = CollectionItem.objects.get_or_create(
            user=self.request.user,
            issue=item.issue,
            defaults={
                "purchase_date": form.cleaned_data.get("purchase_date"),
                "purchase_price": form.cleaned_data.get("purchase_price"),
                "purchase_store": form.cleaned_data.get("purchase_store", ""),
                "notes": form.cleaned_data.get("notes", ""),
                "grade": item.desired_grade,
            },
        )
        item.status = WishListItem.Status.ACQUIRED
        item.save(update_fields=["status", "modified"])
        action = "Added to" if created else "Already in"
        messages.success(
            self.request,
            f"{item.issue} marked as acquired! {action} your collection.",
        )
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("wish-list:detail")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["item"] = self.wish_list_item
        return context


@login_required
@require_POST
def toggle_wish_list_item(request, slug):
    issue = get_object_or_404(Issue, slug=slug)
    wish_list, _ = WishList.objects.get_or_create(user=request.user)
    item, created = WishListItem.objects.get_or_create(wish_list=wish_list, issue=issue)
    if not created:
        item.delete()
        on_wish_list = False
    else:
        on_wish_list = True
    return render(
        request,
        "wish_list/partials/wish_list_button.html",
        {"issue": issue, "on_wish_list": on_wish_list},
    )

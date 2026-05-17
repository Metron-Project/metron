from django.urls import path

from wish_list.views import (
    AcquireWishListItemView,
    WishListDetailView,
    WishListItemDeleteView,
    WishListItemUpdateView,
)

app_name = "wish-list"

urlpatterns = [
    path("", WishListDetailView.as_view(), name="detail"),
    path("item/<int:pk>/update/", WishListItemUpdateView.as_view(), name="item-update"),
    path("item/<int:pk>/delete/", WishListItemDeleteView.as_view(), name="item-delete"),
    path("item/<int:pk>/acquire/", AcquireWishListItemView.as_view(), name="item-acquire"),
]

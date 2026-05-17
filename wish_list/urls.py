from django.urls import path

from wish_list.views import (
    AcquireWishListItemView,
    PublicWishListDetailView,
    WishListDetailView,
    WishListItemDeleteView,
    WishListItemUpdateView,
    WishListSettingsView,
)

app_name = "wish-list"

urlpatterns = [
    path("", WishListDetailView.as_view(), name="detail"),
    path("settings/", WishListSettingsView.as_view(), name="settings"),
    path("<int:pk>/", PublicWishListDetailView.as_view(), name="public-detail"),
    path("item/<int:pk>/update/", WishListItemUpdateView.as_view(), name="item-update"),
    path("item/<int:pk>/delete/", WishListItemDeleteView.as_view(), name="item-delete"),
    path("item/<int:pk>/acquire/", AcquireWishListItemView.as_view(), name="item-acquire"),
]

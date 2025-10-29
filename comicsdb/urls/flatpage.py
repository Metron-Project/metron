from django.contrib.flatpages import views
from django.urls import path

app_name = "flatpage"
urlpatterns = [
    path("about/privacy/", views.flatpage, {"url": "/about/privacy/"}, name="privacy"),
    path("guidelines/api/", views.flatpage, {"url": "/guidelines/api/"}, name="api-guidelines"),
    path(
        "guidelines/editing/",
        views.flatpage,
        {"url": "/guidelines/editing/"},
        name="editing-guidelines",
    ),
]

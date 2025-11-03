"""
Metron URL Configuration
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.i18n import JavaScriptCatalog
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from api import urls as api_urls
from comicsdb.urls import (
    arc as arc_urls,
    character as character_urls,
    creator as creator_urls,
    home as home_urls,
    imprint as imprint_urls,
    issue as issue_urls,
    publisher as publisher_urls,
    series as series_urls,
    team as team_urls,
    universe as universe_urls,
)

handler404 = "metron.views.handler404"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(api_urls)),
    path("api-auth/", include("rest_framework.urls")),
    path("arc/", include(arc_urls)),
    path("character/", include(character_urls)),
    path("creator/", include(creator_urls)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("", include(home_urls)),
    path("imprint/", include(imprint_urls)),
    path("issue/", include(issue_urls)),
    path("jsi18n/", JavaScriptCatalog.as_view(), name="javascript-catalog"),
    path("publisher/", include(publisher_urls)),
    path("select2/", include("django_select2.urls")),
    path("series/", include(series_urls)),
    path("team/", include(team_urls)),
    path("universe/", include(universe_urls)),
    path("accounts/", include("users.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("notifications/", include("django_nyt.urls")),
    path("wiki/", include("wiki.urls")),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

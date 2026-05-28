from django.urls import re_path as url

from wiki.core.plugins import registry
from wiki.core.plugins.base import BasePlugin
from wiki.plugins.editsection import settings, views
from wiki.plugins.editsection.markdown_extensions import EditSectionExtension


class EditSectionPlugin(BasePlugin):
    slug = settings.SLUG
    urlpatterns = {
        "article": [
            url(
                r"^header/(?P<header>[\S]+)/$",
                views.EditSection.as_view(),
                name="editsection",
            ),
        ]
    }

    markdown_extensions = [EditSectionExtension()]


registry.register(EditSectionPlugin)

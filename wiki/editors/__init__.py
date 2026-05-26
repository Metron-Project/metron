from django.urls import get_callable

from wiki.conf import settings

_EditorClass = None
_editor = None


def get_editor_class():
    global _EditorClass
    if not _EditorClass:
        _EditorClass = get_callable(settings.EDITOR)
    return _EditorClass


def get_editor():
    global _editor
    if not _editor:
        _editor = get_editor_class()()
    return _editor

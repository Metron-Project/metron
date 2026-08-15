## Description

<!-- What does this PR do, and why? -->

## Checklist

- [ ] Tests pass locally (`pytest`)
- [ ] Linted (`ruff check . --fix && ruff format .`)
- [ ] New/changed user-facing strings in templates, forms, and views are
      wrapped for translation (`{% trans %}`/`{% blocktrans %}` in templates,
      `gettext`/`gettext_lazy` in Python), and `django-admin makemessages -a`
      was run to update `locale/*/LC_MESSAGES/django.po` for existing
      languages
- [ ] Migrations included, if models changed (`python manage.py makemigrations`)

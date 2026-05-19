from django.conf import settings

CURRENCY_CHOICES = [(c, c) for c in settings.CURRENCIES]

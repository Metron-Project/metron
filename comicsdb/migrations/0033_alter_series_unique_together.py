# Generated by Django 5.1.3 on 2024-12-02 15:38

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("comicsdb", "0032_add_created_by_fields"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="series",
            unique_together={("publisher", "name", "volume", "series_type")},
        ),
    ]

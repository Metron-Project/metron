# Generated by Django 5.1.6 on 2025-02-10 15:19

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("comicsdb", "0036_publisher_country"),
    ]

    operations = [
        migrations.AlterField(
            model_name="character",
            name="alias",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=100),
                blank=True,
                default=list,
                size=None,
            ),
        ),
        migrations.AlterField(
            model_name="creator",
            name="alias",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=100),
                blank=True,
                default=list,
                size=None,
            ),
        ),
        migrations.AlterField(
            model_name="issue",
            name="name",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=150, verbose_name="Story Title"),
                blank=True,
                default=list,
                size=None,
            ),
        ),
    ]

# Generated by Django 5.0.3 on 2024-03-17 18:53

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comicsdb', '0022_alter_team_related_names'),
    ]

    operations = [
        migrations.AlterField(
            model_name='universe',
            name='publisher',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='universes', to='comicsdb.publisher'),
        ),
    ]

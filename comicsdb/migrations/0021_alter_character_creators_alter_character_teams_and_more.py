# Generated by Django 5.0.3 on 2024-03-16 15:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comicsdb', '0020_alter_issue_creators'),
    ]

    operations = [
        migrations.AlterField(
            model_name='character',
            name='creators',
            field=models.ManyToManyField(blank=True, related_name='characters', to='comicsdb.creator'),
        ),
        migrations.AlterField(
            model_name='character',
            name='teams',
            field=models.ManyToManyField(blank=True, related_name='characters', to='comicsdb.team'),
        ),
        migrations.AlterField(
            model_name='character',
            name='universes',
            field=models.ManyToManyField(blank=True, related_name='characters', to='comicsdb.universe'),
        ),
    ]
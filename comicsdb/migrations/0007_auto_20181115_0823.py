# Generated by Django 2.1.3 on 2018-11-15 13:23

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('comicsdb', '0006_auto_20181115_0754'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='credits',
            options={'ordering': ['creator__name'], 'verbose_name_plural': 'Credits'},
        ),
    ]

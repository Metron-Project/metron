# Generated by Django 2.1.3 on 2018-11-15 12:38

from django.db import migrations

def combine_names(apps, schema_editor):
    Creator = apps.get_model('comicsdb', 'Creator')
    for creator in Creator.objects.all():
        creator.name = '%s %s' % (creator.first_name, creator.last_name)
        creator.save()

class Migration(migrations.Migration):

    dependencies = [
        ('comicsdb', '0004_auto_20181115_0724'),
    ]

    operations = [
        migrations.RunPython(combine_names),
    ]

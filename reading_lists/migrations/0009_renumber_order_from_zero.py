from django.db import migrations


def renumber_items_starting_from_zero(apps, schema_editor):
    ReadingList = apps.get_model("reading_lists", "ReadingList")
    ReadingListItem = apps.get_model("reading_lists", "ReadingListItem")

    for reading_list in ReadingList.objects.all():
        items = list(
            ReadingListItem.objects.filter(reading_list=reading_list).order_by("order", "pk")
        )
        if items and items[0].order == 0:
            for new_order, item in enumerate(items, start=1):
                if item.order != new_order:
                    item.order = new_order
                    item.save()


class Migration(migrations.Migration):
    dependencies = [
        ("reading_lists", "0008_fix_order_default"),
    ]

    operations = [
        migrations.RunPython(
            renumber_items_starting_from_zero,
            reverse_code=migrations.RunPython.noop,
        ),
    ]

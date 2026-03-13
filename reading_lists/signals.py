from django.utils import timezone


def update_reading_list_modified_on_item_change(sender, instance, **kwargs):
    from reading_lists.models import ReadingList  # noqa: PLC0415

    ReadingList.objects.filter(pk=instance.reading_list_id).update(modified=timezone.now())

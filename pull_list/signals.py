from django.utils import timezone


def update_pull_list_modified_on_series_change(sender, instance, **kwargs):
    from pull_list.models import PullList  # noqa: PLC0415

    PullList.objects.filter(pk=instance.pull_list_id).update(modified=timezone.now())

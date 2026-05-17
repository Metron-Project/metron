from django.utils import timezone


def update_wish_list_modified_on_item_change(sender, instance, **kwargs):
    from wish_list.models import WishList  # noqa: PLC0415

    WishList.objects.filter(pk=instance.wish_list_id).update(modified=timezone.now())

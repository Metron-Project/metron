from rest_framework import serializers

from api.v1_0.serializers.collection import CollectionIssueSerializer
from wish_list.models import WishList, WishListItem


class WishListItemListSerializer(serializers.ModelSerializer):
    issue = CollectionIssueSerializer(read_only=True)
    status = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = WishListItem
        fields = (
            "id",
            "issue",
            "status",
            "priority",
            "desired_grade",
            "modified",
        )


class WishListItemReadSerializer(serializers.ModelSerializer):
    issue = CollectionIssueSerializer(read_only=True)
    status = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = WishListItem
        fields = (
            "id",
            "issue",
            "status",
            "priority",
            "desired_grade",
            "max_price",
            "notes",
            "added_on",
            "modified",
        )


class WishListSerializer(serializers.ModelSerializer):
    item_count = serializers.IntegerField(read_only=True)
    items_url = serializers.SerializerMethodField()

    def get_items_url(self, obj: WishList) -> str:
        return self.context["request"].build_absolute_uri("/api/wish_list/items/")

    class Meta:
        model = WishList
        fields = ("id", "item_count", "items_url", "modified")


class WishListAddItemSerializer(serializers.Serializer):
    issue_id = serializers.IntegerField()
    priority = serializers.IntegerField(required=False, min_value=1, max_value=5, default=3)
    desired_grade = serializers.DecimalField(
        required=False, allow_null=True, max_digits=3, decimal_places=1
    )
    max_price = serializers.DecimalField(
        required=False, allow_null=True, max_digits=7, decimal_places=2
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_issue_id(self, value):
        from comicsdb.models.issue import Issue  # noqa: PLC0415

        if not Issue.objects.filter(pk=value).exists():
            raise serializers.ValidationError(f"Issue with id {value} does not exist.")
        return value


class AcquireWishListItemSerializer(serializers.Serializer):
    purchase_date = serializers.DateField(required=False, allow_null=True)
    purchase_price = serializers.DecimalField(
        required=False, allow_null=True, max_digits=7, decimal_places=2
    )
    purchase_store = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")

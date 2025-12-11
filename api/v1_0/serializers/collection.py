from rest_framework import serializers

from api.v1_0.serializers.issue import IssueListSeriesSerializer
from api.v1_0.serializers.reading_list import UserSerializer
from comicsdb.models import Issue
from user_collection.models import CollectionItem


class CollectionIssueSerializer(serializers.ModelSerializer):
    """Serializer for issues in collection (without image and cover_hash)."""

    series = IssueListSeriesSerializer(read_only=True)

    class Meta:
        model = Issue
        fields = (
            "id",
            "series",
            "number",
            "cover_date",
            "store_date",
            "modified",
        )


class CollectionListSerializer(serializers.ModelSerializer):
    """List serializer for collection items - minimal data for list view."""

    user = UserSerializer(read_only=True)
    issue = CollectionIssueSerializer(read_only=True)
    book_format = serializers.CharField(source="get_book_format_display", read_only=True)

    class Meta:
        model = CollectionItem
        fields = (
            "id",
            "user",
            "issue",
            "quantity",
            "book_format",
            "purchase_date",
            "is_read",
            "modified",
        )


class CollectionReadSerializer(serializers.ModelSerializer):
    """Read serializer for collection items - full detail view."""

    user = UserSerializer(read_only=True)
    issue = CollectionIssueSerializer(read_only=True)
    book_format = serializers.CharField(source="get_book_format_display", read_only=True)
    resource_url = serializers.SerializerMethodField("get_resource_url")

    def get_resource_url(self, obj: CollectionItem) -> str:
        return self.context["request"].build_absolute_uri(obj.get_absolute_url())

    class Meta:
        model = CollectionItem
        fields = (
            "id",
            "user",
            "issue",
            "quantity",
            "book_format",
            "purchase_date",
            "purchase_price",
            "purchase_store",
            "storage_location",
            "notes",
            "is_read",
            "date_read",
            "resource_url",
            "created_on",
            "modified",
        )


class CollectionSerializer(serializers.ModelSerializer):
    """Write serializer for collection items - create/update operations."""

    class Meta:
        model = CollectionItem
        fields = (
            "id",
            "issue",
            "quantity",
            "book_format",
            "purchase_date",
            "purchase_price",
            "purchase_store",
            "storage_location",
            "notes",
            "is_read",
            "date_read",
        )

    def validate(self, data):
        """Validate that the user doesn't try to create duplicate entries."""
        request = self.context.get("request")
        issue = data.get("issue")

        # Only check for duplicates on create
        if (
            not self.instance
            and request
            and issue
            and CollectionItem.objects.filter(user=request.user, issue=issue).exists()
        ):
            raise serializers.ValidationError(
                {"issue": "This issue is already in your collection."}
            )

        return data

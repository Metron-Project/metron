from rest_framework import serializers

from api.v1_0.serializers.issue import IssueListSeriesSerializer
from comicsdb.models import Issue
from reading_lists.models import ReadingList, ReadingListItem
from users.models import CustomUser


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ("id", "username")


class ReadingListIssueSerializer(serializers.ModelSerializer):
    """Serializer for issues in reading lists (without image and cover_hash)."""

    series = IssueListSeriesSerializer(read_only=True)

    class Meta:
        model = Issue
        fields = (
            "id",
            "series",
            "number",
            "cover_date",
            "store_date",
            "cv_id",
            "gcd_id",
            "modified",
        )


class ReadingListItemSerializer(serializers.ModelSerializer):
    issue = ReadingListIssueSerializer(read_only=True)

    class Meta:
        model = ReadingListItem
        fields = ("id", "issue", "order")


class ReadingListListSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    issue_count = serializers.SerializerMethodField()

    def get_issue_count(self, obj: ReadingList) -> int:
        return obj.issues.count()

    class Meta:
        model = ReadingList
        fields = (
            "id",
            "name",
            "slug",
            "user",
            "is_private",
            "attribution_source",
            "issue_count",
            "modified",
        )


class ReadingListSerializer(serializers.ModelSerializer):
    resource_url = serializers.SerializerMethodField("get_resource_url")
    attribution_source = serializers.ChoiceField(
        choices=ReadingList.AttributionSource.choices,
        required=False,
        allow_blank=True,
    )

    def get_resource_url(self, obj: ReadingList) -> str:
        return self.context["request"].build_absolute_uri(obj.get_absolute_url())

    def create(self, validated_data):
        """Create and return a new ReadingList instance."""
        issues_data = validated_data.pop("issues", None)
        reading_list = ReadingList.objects.create(**validated_data)
        if issues_data:
            reading_list.issues.set(issues_data)
        return reading_list

    def update(self, instance: ReadingList, validated_data):
        """Update and return an existing ReadingList instance."""
        issues_data = validated_data.pop("issues", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if issues_data is not None:
            instance.issues.set(issues_data)

        instance.save()
        return instance

    class Meta:
        model = ReadingList
        fields = (
            "id",
            "user",
            "name",
            "slug",
            "desc",
            "is_private",
            "attribution_source",
            "attribution_url",
            "issues",
            "resource_url",
            "modified",
        )
        read_only_fields = ("slug", "modified")


class ReadingListReadSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    attribution_source = serializers.CharField(
        source="get_attribution_source_display", read_only=True
    )
    resource_url = serializers.SerializerMethodField("get_resource_url")
    items = serializers.SerializerMethodField()
    start_year = serializers.ReadOnlyField()
    end_year = serializers.ReadOnlyField()
    issue_count = serializers.SerializerMethodField()

    def get_resource_url(self, obj: ReadingList) -> str:
        return self.context["request"].build_absolute_uri(obj.get_absolute_url())

    def get_items(self, obj: ReadingList) -> list:
        """Get ordered reading list items with issue details."""
        items = obj.reading_list_items.select_related(
            "issue__series", "issue__series__series_type"
        ).order_by("order")
        return ReadingListItemSerializer(items, many=True, context=self.context).data

    def get_issue_count(self, obj: ReadingList) -> int:
        return obj.issues.count()

    class Meta:
        model = ReadingList
        fields = (
            "id",
            "user",
            "name",
            "slug",
            "desc",
            "is_private",
            "attribution_source",
            "attribution_url",
            "start_year",
            "end_year",
            "issue_count",
            "items",
            "resource_url",
            "modified",
        )

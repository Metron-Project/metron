from django.urls import reverse
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


class ReadingListReadSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    attribution_source = serializers.CharField(
        source="get_attribution_source_display", read_only=True
    )
    resource_url = serializers.SerializerMethodField("get_resource_url")
    items_url = serializers.SerializerMethodField()
    start_year = serializers.ReadOnlyField()
    end_year = serializers.ReadOnlyField()
    issue_count = serializers.SerializerMethodField()

    def get_resource_url(self, obj: ReadingList) -> str:
        return self.context["request"].build_absolute_uri(obj.get_absolute_url())

    def get_items_url(self, obj: ReadingList) -> str:
        """Get the URL to the paginated items endpoint."""

        path = reverse("api:reading_list-items", kwargs={"pk": obj.pk})
        return self.context["request"].build_absolute_uri(path)

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
            "items_url",
            "resource_url",
            "modified",
        )

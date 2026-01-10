from rest_framework import serializers

from api.v1_0.serializers.issue import IssueListSeriesSerializer
from api.v1_0.serializers.publisher import BasicPublisherSerializer
from api.v1_0.serializers.reading_list import UserSerializer
from api.v1_0.serializers.series import SeriesTypeSerializer
from comicsdb.models import Issue, Series
from user_collection.models import CollectionItem, ReadDate


class ReadDateSerializer(serializers.ModelSerializer):
    """Serializer for read dates."""

    class Meta:
        model = ReadDate
        fields = ("id", "read_date", "created_on")


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
    grading_company = serializers.CharField(source="get_grading_company_display", read_only=True)

    class Meta:
        model = CollectionItem
        fields = (
            "id",
            "user",
            "issue",
            "quantity",
            "book_format",
            "grade",
            "grading_company",
            "purchase_date",
            "is_read",
            "rating",
            "modified",
        )


class CollectionReadSerializer(serializers.ModelSerializer):
    """Read serializer for collection items - full detail view."""

    user = UserSerializer(read_only=True)
    issue = CollectionIssueSerializer(read_only=True)
    book_format = serializers.CharField(source="get_book_format_display", read_only=True)
    grading_company = serializers.CharField(source="get_grading_company_display", read_only=True)
    read_dates = ReadDateSerializer(many=True, read_only=True)
    read_count = serializers.IntegerField(source="get_read_count", read_only=True)
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
            "grade",
            "grading_company",
            "purchase_date",
            "purchase_price",
            "purchase_store",
            "storage_location",
            "notes",
            "is_read",
            "date_read",
            "read_dates",
            "read_count",
            "rating",
            "resource_url",
            "created_on",
            "modified",
        )


class MissingSeriesSerializer(serializers.ModelSerializer):
    """Serializer for series with missing issues."""

    publisher = BasicPublisherSerializer(read_only=True)
    series_type = SeriesTypeSerializer(read_only=True)
    total_issues = serializers.IntegerField(read_only=True)
    owned_issues = serializers.IntegerField(read_only=True)
    missing_count = serializers.IntegerField(read_only=True)
    completion_percentage = serializers.SerializerMethodField()

    def get_completion_percentage(self, obj: Series) -> float:
        """Calculate completion percentage."""
        if obj.total_issues > 0:
            return round((obj.owned_issues / obj.total_issues) * 100, 1)
        return 0.0

    class Meta:
        model = Series
        fields = (
            "id",
            "name",
            "sort_name",
            "year_began",
            "year_end",
            "publisher",
            "series_type",
            "total_issues",
            "owned_issues",
            "missing_count",
            "completion_percentage",
        )


class MissingIssueSerializer(serializers.ModelSerializer):
    """Serializer for missing issues in a series."""

    series = IssueListSeriesSerializer(read_only=True)

    class Meta:
        model = Issue
        fields = (
            "id",
            "series",
            "number",
            "cover_date",
            "store_date",
        )


class ScrobbleRequestSerializer(serializers.Serializer):
    """Serializer for scrobble request validation."""

    issue_id = serializers.IntegerField()
    date_read = serializers.DateTimeField(required=False, allow_null=True)
    rating = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=5)

    def validate_issue_id(self, value):
        """Verify issue exists."""
        try:
            Issue.objects.get(pk=value)
        except Issue.DoesNotExist as err:
            raise serializers.ValidationError(f"Issue with id {value} does not exist.") from err
        return value


class ScrobbleResponseSerializer(serializers.ModelSerializer):
    """Serializer for scrobble response."""

    issue = CollectionIssueSerializer(read_only=True)
    created = serializers.BooleanField(read_only=True)

    class Meta:
        model = CollectionItem
        fields = (
            "id",
            "issue",
            "is_read",
            "date_read",
            "rating",
            "created",
            "modified",
        )

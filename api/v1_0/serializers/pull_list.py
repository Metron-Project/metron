from rest_framework import serializers

from api.v1_0.serializers.series import SeriesListSerializer
from pull_list.models import PullList, PullListSeries


class PullListSeriesSerializer(serializers.ModelSerializer):
    series = SeriesListSerializer(read_only=True)

    class Meta:
        model = PullListSeries
        fields = ("id", "series", "added_on")


class PullListReadSerializer(serializers.ModelSerializer):
    series_count = serializers.IntegerField(read_only=True)
    series_url = serializers.SerializerMethodField()

    def get_series_url(self, obj: PullList) -> str:
        return self.context["request"].build_absolute_uri("/api/pull_list/series/")

    class Meta:
        model = PullList
        fields = ("id", "is_private", "series_count", "series_url", "modified")

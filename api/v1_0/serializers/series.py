from rest_framework import serializers

from api.v1_0.serializers.genre import GenreSerializer
from api.v1_0.serializers.imprint import BasicImprintSerializer
from api.v1_0.serializers.publisher import BasicPublisherSerializer
from comicsdb.models import Series, SeriesType


class SeriesListSerializer(serializers.ModelSerializer):
    series = serializers.CharField(source="__str__")
    issue_count = serializers.ReadOnlyField()

    class Meta:
        model = Series
        fields = ("id", "series", "year_began", "volume", "issue_count", "modified")


class SeriesTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeriesType
        fields = ("id", "name")


class AssociatedSeriesSerializer(serializers.ModelSerializer):
    series = serializers.CharField(source="__str__")

    class Meta:
        model = Series
        fields = ("id", "series")


class SeriesSerializer(serializers.ModelSerializer):
    resource_url = serializers.SerializerMethodField("get_resource_url")
    status = serializers.ChoiceField(choices=Series.Status.choices)

    def get_resource_url(self, obj: Series) -> str:
        return self.context["request"].build_absolute_uri(obj.get_absolute_url())

    def create(self, validated_data):
        """
        Create and return a new `Series` instance, given the validated data.
        """
        genres_data = validated_data.pop("genres", None)
        assoc_data = validated_data.pop("associated", None)
        series = Series.objects.create(**validated_data)
        if genres_data:
            series.genres.add(*genres_data)
        if assoc_data:
            series.associated.add(*assoc_data)
        return series

    def update(self, instance: Series, validated_data):
        """
        Update and return an existing `Series` instance, given the validated data.
        """
        genres_data = validated_data.pop("genres", None)
        assoc_data = validated_data.pop("associated", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if genres_data is not None:
            instance.genres.set(genres_data)
        if assoc_data is not None:
            instance.associated.set(assoc_data)

        instance.save()
        return instance

    class Meta:
        model = Series
        fields = (
            "id",
            "name",
            "sort_name",
            "volume",
            "series_type",
            "status",
            "publisher",
            "imprint",
            "year_began",
            "year_end",
            "desc",
            "issue_count",
            "genres",
            "associated",
            "cv_id",
            "gcd_id",
            "resource_url",
            "modified",
        )


class SeriesReadSerializer(SeriesSerializer):
    publisher = BasicPublisherSerializer(read_only=True)
    imprint = BasicImprintSerializer(read_only=True)
    series_type = SeriesTypeSerializer(read_only=True)
    status = serializers.CharField(source="get_status_display", read_only=True)
    issue_count = serializers.ReadOnlyField()
    associated = AssociatedSeriesSerializer(many=True, read_only=True)
    genres = GenreSerializer(many=True, read_only=True)

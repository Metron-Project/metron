from rest_framework import serializers

from api.v1_0.serializers import CreditReadSerializer
from api.v1_0.serializers.arc import ArcListSerializer
from api.v1_0.serializers.character import CharacterListSerializer
from api.v1_0.serializers.genre import GenreSerializer
from api.v1_0.serializers.imprint import BasicImprintSerializer
from api.v1_0.serializers.publisher import BasicPublisherSerializer
from api.v1_0.serializers.rating import RatingSerializer
from api.v1_0.serializers.series import SeriesTypeSerializer
from api.v1_0.serializers.team import TeamListSerializer
from api.v1_0.serializers.universe import UniverseListSerializer
from comicsdb.models import Issue, Series, Variant


class VariantsIssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Variant
        fields = ("name", "sku", "upc", "image")


class IssueSeriesSerializer(serializers.ModelSerializer):
    series_type = SeriesTypeSerializer(read_only=True)
    genres = GenreSerializer(many=True, read_only=True)

    class Meta:
        model = Series
        fields = ("id", "name", "sort_name", "volume", "year_began", "series_type", "genres")


class IssueListSeriesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Series
        fields = ("name", "volume", "year_began")


class IssueListSerializer(serializers.ModelSerializer):
    issue = serializers.CharField(source="__str__")
    series = IssueListSeriesSerializer(read_only=True)

    class Meta:
        model = Issue
        fields = (
            "id",
            "series",
            "number",
            "issue",
            "cover_date",
            "store_date",
            "image",
            "cover_hash",
            "modified",
        )


class ReprintSerializer(serializers.ModelSerializer):
    issue = serializers.CharField(source="__str__")

    class Meta:
        model = Issue
        fields = ("id", "issue")


# TODO: Refactor this so reuse Issue serializer for read-only also.
#       Need to handle variants & credits sets.
class IssueSerializer(serializers.ModelSerializer):
    resource_url = serializers.SerializerMethodField("get_resource_url")

    def get_resource_url(self, obj: Issue) -> str:
        return self.context["request"].build_absolute_uri(obj.get_absolute_url())

    def create(self, validated_data):
        """
        Create and return a new `Issue` instance, given the validated data.
        """
        arcs_data = validated_data.pop("arcs", None)
        characters_data = validated_data.pop("characters", None)
        teams_data = validated_data.pop("teams", None)
        universes_data = validated_data.pop("universes", None)
        reprints_data = validated_data.pop("reprints", None)
        if "image" in validated_data and validated_data["image"] is not None:
            validated_data["image"] = validated_data["image"]
        issue: Issue = Issue.objects.create(**validated_data)
        if arcs_data:
            issue.arcs.add(*arcs_data)
        if characters_data:
            issue.characters.add(*characters_data)
        if teams_data:
            issue.teams.add(*teams_data)
        if universes_data:
            issue.universes.add(*universes_data)
        if reprints_data:
            issue.reprints.add(*reprints_data)
        return issue

    def update(self, instance: Issue, validated_data):
        """
        Update and return an existing `Issue` instance, given the validated data.
        """
        instance.series = validated_data.get("series", instance.series)
        instance.number = validated_data.get("number", instance.number)
        instance.alt_number = validated_data.get("alt_number", instance.alt_number)
        instance.title = validated_data.get("title", instance.title)
        instance.name = validated_data.get("name", instance.name)
        instance.cover_date = validated_data.get("cover_date", instance.cover_date)
        instance.store_date = validated_data.get("store_date", instance.store_date)
        instance.foc_date = validated_data.get("foc_date", instance.foc_date)
        instance.price = validated_data.get("price", instance.price)
        instance.rating = validated_data.get("rating", instance.rating)
        instance.sku = validated_data.get("sku", instance.sku)
        instance.isbn = validated_data.get("isbn", instance.isbn)
        instance.upc = validated_data.get("upc", instance.upc)
        instance.page = validated_data.get("page", instance.page)
        instance.desc = validated_data.get("desc", instance.desc)
        instance.image = validated_data.get("image", instance.image)
        instance.cv_id = validated_data.get("cv_id", instance.cv_id)
        instance.gcd_id = validated_data.get("gcd_id", instance.gcd_id)
        if arcs_data := validated_data.pop("arcs", None):
            instance.arcs.add(*arcs_data)
        if characters_data := validated_data.pop("characters", None):
            instance.characters.add(*characters_data)
        if teams_data := validated_data.pop("teams", None):
            instance.teams.add(*teams_data)
        if universes_data := validated_data.pop("universes", None):
            instance.universes.add(*universes_data)
        if reprints_data := validated_data.pop("reprints", None):
            instance.reprints.add(*reprints_data)
        instance.save()
        return instance

    class Meta:
        model = Issue
        fields = (
            "id",
            "series",
            "number",
            "alt_number",
            "title",
            "name",
            "cover_date",
            "store_date",
            "foc_date",
            "price",
            "rating",
            "sku",
            "isbn",
            "upc",
            "page",
            "desc",
            "image",
            "arcs",
            "characters",
            "teams",
            "universes",
            "reprints",
            "cv_id",
            "gcd_id",
            "resource_url",
        )


class IssueReadSerializer(serializers.ModelSerializer):
    variants = VariantsIssueSerializer("variants", many=True, read_only=True)
    credits = CreditReadSerializer(source="credits_set", many=True, read_only=True)
    arcs = ArcListSerializer(many=True, read_only=True)
    characters = CharacterListSerializer(many=True, read_only=True)
    teams = TeamListSerializer(many=True, read_only=True)
    universes = UniverseListSerializer(many=True, read_only=True)
    publisher = BasicPublisherSerializer(source="series.publisher", read_only=True)
    imprint = BasicImprintSerializer(source="series.imprint", read_only=True)
    series = IssueSeriesSerializer(read_only=True)
    reprints = ReprintSerializer(many=True, read_only=True)
    rating = RatingSerializer(read_only=True)
    resource_url = serializers.SerializerMethodField("get_resource_url")

    def get_resource_url(self, obj: Issue) -> str:
        return self.context["request"].build_absolute_uri(obj.get_absolute_url())

    class Meta:
        model = Issue
        fields = (
            "id",
            "publisher",
            "imprint",
            "series",
            "number",
            "alt_number",
            "title",
            "name",
            "cover_date",
            "store_date",
            "foc_date",
            "price",
            "rating",
            "sku",
            "isbn",
            "upc",
            "page",
            "desc",
            "image",
            "cover_hash",
            "arcs",
            "credits",
            "characters",
            "teams",
            "universes",
            "reprints",
            "variants",
            "cv_id",
            "gcd_id",
            "resource_url",
            "modified",
        )

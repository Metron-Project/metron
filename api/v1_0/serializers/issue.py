from decimal import Decimal

from djmoney.money import Money
from drf_spectacular.utils import extend_schema_field
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


@extend_schema_field(
    {
        "type": "string",
        "format": "decimal",
        "pattern": r"^\d+\.\d{2}$",
        "example": "3.99",
        "description": (
            "Price amount as decimal string (e.g., '3.99'). "
            "Currency information available in price_currency field."
        ),
        "nullable": True,
    }
)
class PriceField(serializers.Field):
    """
    Custom field for backward-compatible price serialization.

    For READ operations:
    - Returns decimal amount only (e.g., "3.99") for backward compatibility
    - Clients can optionally use price_currency field for currency info

    For WRITE operations:
    - Accepts decimal value (e.g., 3.99) and defaults to USD
    - Can also accept {"amount": 3.99, "currency": "USD"} for multi-currency
    """

    def to_representation(self, value):
        """
        Serialize MoneyField to decimal string for backward compatibility.
        Returns: "3.99" (just the amount, no currency)
        """
        if value is None:
            return None
        if isinstance(value, Money):
            return str(value.amount)
        return str(value)

    def to_internal_value(self, data):
        """
        Deserialize input to Money object.
        Accepts:
        - None or empty string: returns None (blank price)
        - Decimal/float/string: "3.99" (defaults to USD)
        - Dict: {"amount": 3.99, "currency": "USD"}
        """
        # Handle None, empty string, or empty dict
        if data in (None, "", {}):
            return None

        # Handle dict format for multi-currency support
        if isinstance(data, dict):
            amount = data.get("amount")
            currency = data.get("currency", "USD")

            # Allow empty/null amount in dict format
            if amount in (None, ""):
                return None

            try:
                return Money(Decimal(str(amount)), currency)
            except (ValueError, TypeError) as e:
                raise serializers.ValidationError(f"Invalid price format: {e}") from e

        # Handle simple decimal/string format (backward compatible)
        # Convert to string and strip whitespace
        data_str = str(data).strip()
        if not data_str:
            return None

        try:
            return Money(Decimal(data_str), "USD")
        except (ValueError, TypeError) as e:
            raise serializers.ValidationError(f"Invalid price format: {e}") from e


class VariantsIssueSerializer(serializers.ModelSerializer):
    price = PriceField(read_only=True)

    class Meta:
        model = Variant
        fields = ("name", "price", "sku", "upc", "image")


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
    price = PriceField(required=False, allow_null=True)
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
        issue: Issue = Issue.objects.create(**validated_data)
        if arcs_data:
            issue.arcs.set(arcs_data)
        if characters_data:
            issue.characters.set(characters_data)
        if teams_data:
            issue.teams.set(teams_data)
        if universes_data:
            issue.universes.set(universes_data)
        if reprints_data:
            issue.reprints.set(reprints_data)
        return issue

    def update(self, instance: Issue, validated_data):
        """
        Update and return an existing `Issue` instance, given the validated data.
        """
        # Extract M2M fields before updating
        arcs_data = validated_data.pop("arcs", None)
        characters_data = validated_data.pop("characters", None)
        teams_data = validated_data.pop("teams", None)
        universes_data = validated_data.pop("universes", None)
        reprints_data = validated_data.pop("reprints", None)

        # Update all regular fields at once
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Update M2M relationships (replace existing)
        if arcs_data is not None:
            instance.arcs.set(arcs_data)
        if characters_data is not None:
            instance.characters.set(characters_data)
        if teams_data is not None:
            instance.teams.set(teams_data)
        if universes_data is not None:
            instance.universes.set(universes_data)
        if reprints_data is not None:
            instance.reprints.set(reprints_data)

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
    price = PriceField(read_only=True)
    price_currency = serializers.SerializerMethodField()
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

    def get_price_currency(self, obj: Issue) -> str:
        """Return the currency code for the price field."""
        if obj.price and isinstance(obj.price, Money):
            return str(obj.price.currency)
        return ""

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
            "price_currency",
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

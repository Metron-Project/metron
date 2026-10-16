from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from comicsdb.models import Attribution

# Fixed, untranslated names so API output doesn't vary with the request's language (and can be
# cached per object), unlike the model's translatable choice labels.
SOURCE_NAMES = {
    Attribution.Source.MARVEL: "Marvel",
    Attribution.Source.WIKIPEDIA: "Wikipedia",
    Attribution.Source.GCD: "Grand Comics Database",
    Attribution.Source.DC: "DC",
}


class AttributionSerializer(serializers.ModelSerializer):
    source = serializers.SerializerMethodField()

    class Meta:
        model = Attribution
        fields = ("source", "url")

    @extend_schema_field(serializers.ChoiceField(choices=list(SOURCE_NAMES.values())))
    def get_source(self, obj: Attribution) -> str:
        return SOURCE_NAMES[obj.source]

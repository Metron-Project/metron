from rest_framework import serializers

from comicsdb.models import Attribution


class AttributionSerializer(serializers.ModelSerializer):
    source = serializers.CharField(source="get_source_display", read_only=True)

    class Meta:
        model = Attribution
        fields = ("source", "url")

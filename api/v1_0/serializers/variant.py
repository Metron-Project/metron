from rest_framework import serializers

from comicsdb.models import Variant
from comicsdb.validators import clean_upc


class VariantSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        """
        Validate the UPC's check digit against the issue's cover date, falling back to the
        instance's values for whichever a partial update omits.
        """
        issue = attrs.get("issue", getattr(self.instance, "issue", None))
        clean_upc(
            attrs.get("upc", getattr(self.instance, "upc", "")), getattr(issue, "cover_date", None)
        )
        return attrs

    def update(self, instance: Variant, validated_data):
        """
        Update and return an existing `Variant` instance, given the validated data.
        """
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    class Meta:
        model = Variant
        fields = "__all__"

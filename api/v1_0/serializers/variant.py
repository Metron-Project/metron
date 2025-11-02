from rest_framework import serializers

from comicsdb.models import Variant


class VariantSerializer(serializers.ModelSerializer):
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

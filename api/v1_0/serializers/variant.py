from rest_framework import serializers

from comicsdb.models import Variant


class VariantSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        """
        Create and return a new `Variant` instance, given the validated data.
        """
        return Variant.objects.create(**validated_data)

    def update(self, instance: Variant, validated_data):
        """
        Update and return an existing `Variant` instance, given the validated data.
        """
        instance.issue = validated_data.get("issue", instance.issue)
        instance.image = validated_data.get("image", instance.image)
        instance.name = validated_data.get("name", instance.name)
        instance.sku = validated_data.get("sku", instance.sku)
        instance.upc = validated_data.get("upc", instance.upc)
        instance.save()
        return instance

    class Meta:
        model = Variant
        fields = "__all__"

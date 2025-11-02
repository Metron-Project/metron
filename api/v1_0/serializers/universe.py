from rest_framework import serializers

from api.v1_0.serializers import BasicPublisherSerializer
from comicsdb.models import Universe


class UniverseListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Universe
        fields = ("id", "name", "modified")


class UniverseSerializer(serializers.ModelSerializer):
    resource_url = serializers.SerializerMethodField("get_resource_url")

    def get_resource_url(self, obj: Universe) -> str:
        return self.context["request"].build_absolute_uri(obj.get_absolute_url())

    def update(self, instance: Universe, validated_data):
        """
        Update and return an existing `Universe` instance, given the validated data.
        """
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    class Meta:
        model = Universe
        fields = (
            "id",
            "publisher",
            "name",
            "designation",
            "desc",
            "gcd_id",
            "image",
            "resource_url",
            "modified",
        )


class UniverseReadSerializer(UniverseSerializer):
    publisher = BasicPublisherSerializer(read_only=True)

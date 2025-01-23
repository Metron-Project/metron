from rest_framework import serializers

from api.v1_0.serializers import BasicPublisherSerializer
from comicsdb.models import Team, Universe


class UniverseListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Universe
        fields = ("id", "name", "modified")


class UniverseSerializer(serializers.ModelSerializer):
    resource_url = serializers.SerializerMethodField("get_resource_url")

    def get_resource_url(self, obj: Team) -> str:
        return self.context["request"].build_absolute_uri(obj.get_absolute_url())

    def create(self, validated_data):
        """
        Create and return a new `Universe` instance, given the validated data.
        """

        if "image" in validated_data and validated_data["image"] is not None:
            validated_data["image"] = validated_data["image"]
        return Universe.objects.create(**validated_data)

    def update(self, instance: Universe, validated_data):
        """
        Update and return an existing `Universe` instance, given the validated data.
        """
        instance.publisher = validated_data.get("publisher", instance.publisher)
        instance.name = validated_data.get("name", instance.name)
        instance.designation = validated_data.get("designation", instance.designation)
        instance.desc = validated_data.get("desc", instance.desc)
        instance.gcd_id = validated_data.get("gcd_id", instance.gcd_id)
        instance.image = validated_data.get("image", instance.image)
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

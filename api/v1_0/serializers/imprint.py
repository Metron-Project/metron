from rest_framework import serializers

from api.v1_0.serializers import BasicPublisherSerializer
from comicsdb.models import Imprint


class ImprintListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Imprint
        fields = ("id", "name", "modified")


class ImprintSerializer(serializers.ModelSerializer):
    resource_url = serializers.SerializerMethodField("get_resource_url")

    def get_resource_url(self, obj: Imprint) -> str:
        return self.context["request"].build_absolute_uri(obj.get_absolute_url())

    def create(self, validated_data) -> Imprint:
        if "image" in validated_data and validated_data["image"] is not None:
            validated_data["image"] = validated_data["image"]
        return Imprint.objects.create(**validated_data)

    def update(self, instance: Imprint, validated_data) -> Imprint:
        instance.name = validated_data.get("name", instance.name)
        instance.founded = validated_data.get("founded", instance.founded)
        instance.desc = validated_data.get("desc", instance.desc)
        instance.image = validated_data.get("image", instance.image)
        instance.cv_id = validated_data.get("cv_id", instance.cv_id)
        instance.gcd_id = validated_data.get("gcd_id", instance.gcd_id)
        instance.publisher = validated_data.get("publisher", instance.publisher)
        instance.save()
        return instance

    class Meta:
        model = Imprint
        fields = (
            "id",
            "name",
            "founded",
            "desc",
            "image",
            "cv_id",
            "gcd_id",
            "publisher",
            "resource_url",
            "modified",
        )


class ImprintReadSerializer(ImprintSerializer):
    publisher = BasicPublisherSerializer(read_only=True)


class BasicImprintSerializer(serializers.ModelSerializer):
    class Meta:
        model = Imprint
        fields = ("id", "name")

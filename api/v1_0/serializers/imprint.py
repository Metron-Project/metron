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

    def update(self, instance: Imprint, validated_data) -> Imprint:
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
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

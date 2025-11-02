from django_countries.serializers import CountryFieldMixin
from rest_framework import serializers

from comicsdb.models import Publisher


class PublisherListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publisher
        fields = ("id", "name", "modified")


class PublisherSerializer(CountryFieldMixin, serializers.ModelSerializer):
    resource_url = serializers.SerializerMethodField("get_resource_url")

    def get_resource_url(self, obj: Publisher) -> str:
        return self.context["request"].build_absolute_uri(obj.get_absolute_url())

    def update(self, instance: Publisher, validated_data):
        """
        Update and return an existing `Publisher` instance, given the validated data.
        """
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    class Meta:
        model = Publisher
        fields = (
            "id",
            "name",
            "founded",
            "country",
            "desc",
            "image",
            "cv_id",
            "gcd_id",
            "resource_url",
            "modified",
        )


class BasicPublisherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publisher
        fields = ("id", "name")

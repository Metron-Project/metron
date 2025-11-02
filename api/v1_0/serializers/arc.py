from rest_framework import serializers

from comicsdb.models import Arc


class ArcListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Arc
        fields = ("id", "name", "modified")


class ArcSerializer(serializers.ModelSerializer):
    resource_url = serializers.SerializerMethodField("get_resource_url")

    def get_resource_url(self, obj: Arc) -> str:
        return self.context["request"].build_absolute_uri(obj.get_absolute_url())

    def update(self, instance: Arc, validated_data):
        """
        Update and return an existing `Arc` instance, given the validated data.
        """
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    class Meta:
        model = Arc
        fields = ("id", "name", "desc", "image", "cv_id", "gcd_id", "resource_url", "modified")

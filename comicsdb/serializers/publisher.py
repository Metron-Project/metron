from rest_framework import serializers

from comicsdb.models import Publisher


class PublisherListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publisher
        fields = ("id", "name", "modified")


class PublisherSerializer(serializers.ModelSerializer):
    resource_url = serializers.SerializerMethodField("get_resource_url")

    def get_resource_url(self, obj: Publisher) -> str:
        return self.context["request"].build_absolute_uri(obj.get_absolute_url())

    def create(self, validated_data):
        """
        Create and return a new `Publisher` instance, given the validated data.
        """
        if "image" in validated_data and validated_data["image"] is not None:
            validated_data["image"] = validated_data["image"]
        return Publisher.objects.create(**validated_data)

    def update(self, instance: Publisher, validated_data):
        """
        Update and return an existing `Publisher` instance, given the validated data.
        """
        instance.name = validated_data.get("name", instance.name)
        instance.founded = validated_data.get("founded", instance.founded)
        instance.desc = validated_data.get("desc", instance.desc)
        instance.image = validated_data.get("image", instance.image)
        instance.cv_id = validated_data.get("cv_id", instance.cv_id)
        instance.gcd_id = validated_data.get("gcd_id", instance.gcd_id)
        instance.save()
        return instance

    class Meta:
        model = Publisher
        fields = (
            "id",
            "name",
            "founded",
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

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

    def create(self, validated_data):
        """
        Create and return a new `Arc` instance, given the validated data.
        """
        if "image" in validated_data and validated_data["image"] is not None:
            validated_data["image"] = validated_data["image"]
        return Arc.objects.create(**validated_data)

    def update(self, instance: Arc, validated_data):
        """
        Update and return an existing `Arc` instance, given the validated data.
        """
        instance.name = validated_data.get("name", instance.name)
        instance.desc = validated_data.get("desc", instance.desc)
        instance.image = validated_data.get("image", instance.image)
        instance.cv_id = validated_data.get("cv_id", instance.cv_id)
        instance.gcd_id = validated_data.get("gcd_id", instance.gcd_id)
        instance.save()
        return instance

    class Meta:
        model = Arc
        fields = ("id", "name", "desc", "image", "cv_id", "gcd_id", "resource_url", "modified")

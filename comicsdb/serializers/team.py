from rest_framework import serializers

from comicsdb.models import Team
from comicsdb.serializers.creator import CreatorListSerializer
from comicsdb.serializers.universe import UniverseListSerializer


class TeamListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ("id", "name", "modified")


class TeamSerializer(serializers.ModelSerializer):
    resource_url = serializers.SerializerMethodField("get_resource_url")

    def get_resource_url(self, obj: Team) -> str:
        return self.context["request"].build_absolute_uri(obj.get_absolute_url())

    def create(self, validated_data):
        """
        Create and return a new `Team` instance, given the validated data.
        """
        creators_data = validated_data.pop("creators", None)
        universes_data = validated_data.pop("universes", None)
        if "image" in validated_data and validated_data["image"] is not None:
            validated_data["image"] = validated_data["image"]
        team = Team.objects.create(**validated_data)
        if creators_data:
            team.creators.add(*creators_data)
        if universes_data:
            team.universes.add(*universes_data)
        return team

    def update(self, instance: Team, validated_data):
        """
        Update and return an existing `Team` instance, given the validated data.
        """
        instance.name = validated_data.get("name", instance.name)
        instance.desc = validated_data.get("desc", instance.desc)
        instance.image = validated_data.get("image", instance.image)
        instance.cv_id = validated_data.get("cv_id", instance.cv_id)
        instance.gcd_id = validated_data.get("gcd_id", instance.gcd_id)
        if creators_data := validated_data.pop("creators", None):
            instance.creators.add(*creators_data)
        if universes_data := validated_data.pop("universes", None):
            instance.universes.add(*universes_data)
        instance.save()
        return instance

    class Meta:
        model = Team
        fields = (
            "id",
            "name",
            "desc",
            "image",
            "creators",
            "universes",
            "cv_id",
            "gcd_id",
            "resource_url",
            "modified",
        )


class TeamReadSerializer(TeamSerializer):
    creators = CreatorListSerializer(many=True, read_only=True)
    universes = UniverseListSerializer(many=True, read_only=True)

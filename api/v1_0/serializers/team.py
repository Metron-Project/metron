from rest_framework import serializers

from api.v1_0.serializers.creator import CreatorListSerializer
from api.v1_0.serializers.universe import UniverseListSerializer
from comicsdb.models import Team


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
        creators_data = validated_data.pop("creators", None)
        universes_data = validated_data.pop("universes", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if creators_data is not None:
            instance.creators.set(creators_data)
        if universes_data is not None:
            instance.universes.set(universes_data)

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

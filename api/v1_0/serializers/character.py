from rest_framework import serializers

from api.v1_0.serializers.creator import CreatorListSerializer
from api.v1_0.serializers.team import TeamListSerializer
from api.v1_0.serializers.universe import UniverseListSerializer
from comicsdb.models import Character


class CharacterListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Character
        fields = ("id", "name", "modified")


class CharacterSerializer(serializers.ModelSerializer):
    resource_url = serializers.SerializerMethodField("get_resource_url")

    def get_resource_url(self, obj: Character) -> str:
        return self.context["request"].build_absolute_uri(obj.get_absolute_url())

    def create(self, validated_data):
        """
        Create and return a new `Character` instance, given the validated data.
        """
        creators_data = validated_data.pop("creators", None)
        teams_data = validated_data.pop("teams", None)
        universes_data = validated_data.pop("universes", None)
        character = Character.objects.create(**validated_data)
        if creators_data:
            character.creators.add(*creators_data)
        if teams_data:
            character.teams.add(*teams_data)
        if universes_data:
            character.universes.add(*universes_data)
        return character

    def update(self, instance: Character, validated_data):
        """
        Update and return an existing `Character` instance, given the validated data.
        """
        creators_data = validated_data.pop("creators", None)
        teams_data = validated_data.pop("teams", None)
        universes_data = validated_data.pop("universes", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if creators_data is not None:
            instance.creators.set(creators_data)
        if teams_data is not None:
            instance.teams.set(teams_data)
        if universes_data is not None:
            instance.universes.set(universes_data)

        instance.save()
        return instance

    class Meta:
        model = Character
        fields = (
            "id",
            "name",
            "alias",
            "desc",
            "image",
            "creators",
            "teams",
            "universes",
            "cv_id",
            "gcd_id",
            "resource_url",
            "modified",
        )


class CharacterReadSerializer(CharacterSerializer):
    creators = CreatorListSerializer(many=True, read_only=True)
    teams = TeamListSerializer(many=True, read_only=True)
    universes = UniverseListSerializer(many=True, read_only=True)

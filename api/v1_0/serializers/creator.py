from rest_framework import serializers

from comicsdb.models import Creator, Credits, Role


class CreatorListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Creator
        fields = ("id", "name", "modified")


class CreatorSerializer(serializers.ModelSerializer):
    resource_url = serializers.SerializerMethodField("get_resource_url")

    def get_resource_url(self, obj: Creator) -> str:
        return self.context["request"].build_absolute_uri(obj.get_absolute_url())

    def update(self, instance: Creator, validated_data):
        """
        Update and return an existing `Creator` instance, given the validated data.
        """
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    class Meta:
        model = Creator
        fields = (
            "id",
            "name",
            "birth",
            "death",
            "desc",
            "image",
            "alias",
            "cv_id",
            "gcd_id",
            "resource_url",
            "modified",
        )


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ("id", "name")


class CreditSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        """
        Create and return a new `Credits` instance, given the validated data.
        """
        roles_data = validated_data.pop("role", None)
        credit = Credits.objects.create(**validated_data)
        if roles_data:
            credit.role.add(*roles_data)
        return credit

    def update(self, instance: Credits, validated_data):
        """
        Update and return an existing `Credits` instance, given the validated data.
        """
        roles_data = validated_data.pop("role", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if roles_data is not None:
            instance.role.set(roles_data)

        instance.save()
        return instance

    class Meta:
        model = Credits
        fields = "__all__"


class CreditReadSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source="creator.id")
    creator = serializers.ReadOnlyField(source="creator.name")
    role = RoleSerializer("role", many=True)

    class Meta:
        model = Credits
        fields = ("id", "creator", "role")

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

    def create(self, validated_data):
        """
        Create and return a new `Creator` instance, given the validated data.
        """
        if "image" in validated_data and validated_data["image"] is not None:
            validated_data["image"] = validated_data["image"]
        return Creator.objects.create(**validated_data)

    def update(self, instance: Creator, validated_data):
        """
        Update and return an existing `Character` instance, given the validated data.
        """
        instance.name = validated_data.get("name", instance.name)
        instance.desc = validated_data.get("desc", instance.desc)
        instance.image = validated_data.get("image", instance.image)
        instance.alias = validated_data.get("alias", instance.alias)
        instance.birth = validated_data.get("birth", instance.birth)
        instance.death = validated_data.get("death", instance.death)
        instance.cv_id = validated_data.get("cv_id", instance.cv_id)
        instance.gcd_id = validated_data.get("gcd_id", instance.gcd_id)
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
        instance.issue = validated_data.get("issue", instance.issue)
        instance.creator = validated_data.get("creator", instance.creator)
        if roles_data := validated_data.pop("role", None):
            instance.role.add(*roles_data)
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

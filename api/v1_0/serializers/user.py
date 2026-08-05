from rest_framework import serializers


class WhoAmISerializer(serializers.Serializer):
    username = serializers.CharField(read_only=True)

from rest_framework import serializers
from users.models import *

class AddressDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ["id", "address", "city", "postcode", "title", "apartment_name","unit"]


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        exclude = ["user"]

    def validate(self, data):
        request = self.context.get("request")
        user = request.user

        if self.instance is None:
            if Address.objects.filter(user=user).count() >= 2:
                raise serializers.ValidationError(
                    "شما فقط می‌توانید حداکثر ۲ آدرس ثبت کنید."
                )

        return data

    def create(self, validated_data):
        request = self.context.get("request")
        return Address.objects.create(
            user=request.user,
            **validated_data
        )

class UpdateAddressSerializer(serializers.Serializer):
    city = serializers.CharField(required=False)
    postcode = serializers.IntegerField(required=False)
    title = serializers.CharField(required=False)
    apartment_name = serializers.CharField(required=False)
    address = serializers.CharField(required=False)
    unit = serializers.IntegerField(required=False)

    def update(self, instance, validated_data):

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        return instance
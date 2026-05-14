from django.db import transaction
from rest_framework import serializers

from .models import *

# serializers.py
#قیمت و درصد برای سفارش های فوری وارد میکند
class RushFeeSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = RushFeeSetting
        fields = '__all__'
#ظرفیت برای تحویل گرفتن مشخص میکنه
class PickupTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickUpTemplate
        fields = '__all__'

class DeliveryTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryTemplate
        fields = '__all__'

class UpdateRushFeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RushFeeSetting
        fields = '__all__'

        def update(self, instance, validated_data):
            for attr, value in validated_data.items():
                setattr(instance, attr, value)

            instance.save()
            return instance

class UpdatePickupTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickUpTemplate
        fields = '__all__'

        def update(self, instance, validated_data):
            for attr, value in validated_data.items():
                setattr(instance, attr, value)

            instance.save()
            return instance


class UpdateDeliveryTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryTemplate
        fields = '__all__'

        def update(self, instance, validated_data):
            for attr, value in validated_data.items():
                setattr(instance, attr, value)

            instance.save()
            return instance


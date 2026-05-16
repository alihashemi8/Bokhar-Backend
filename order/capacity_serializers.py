from rest_framework import serializers
from .models import RushFeeSetting, PickUpTemplate, DeliveryTemplate

class RushFeeSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = RushFeeSetting
        fields = [
            "id",
            "is_24h_enabled",
            "is_48h_enabled",
            "fee_24h",
            "fee_48h",
            "percent_24h",
            "percent_48h",
            "updated_at",
        ]


class DeliveryTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryTemplate
        fields = [
            'id',
            'time_shift',
            'urgent_24_capacity',
            'urgent_48_capacity',
            'disabled_dates', 
            'base_price',
            'price_add',
            'is_active'
        ]

class PickupTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickUpTemplate
        fields = '__all__'

class DeliveryTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryTemplate
        fields = '__all__'

class UpdatePickupTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickUpTemplate
        fields = '__all__'

class UpdateDeliveryTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryTemplate
        fields = '__all__'

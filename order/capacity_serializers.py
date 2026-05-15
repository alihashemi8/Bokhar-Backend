from rest_framework import serializers
from .models import RushFeeSetting, PickUpTemplate, DeliveryTemplate

class RushFeeSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = RushFeeSetting
        fields = [
            'id', 
            'is_active',
            'tomorrow_fee', 
            'percent_tomorrow_fee',
            'day_after_tomorrow_fee', 
            'percent_day_after_tomorrow_fee',
            'updated_at'
        ]
        read_only_fields = ['updated_at']

class DeliveryTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryTemplate
        fields = [
            'id',
            'time_shift',
            'urgent_24_capacity',
            'urgent_48_capacity',
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

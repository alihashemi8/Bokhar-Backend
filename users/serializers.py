from rest_framework import serializers
from .models import User

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["username", "phone", "email"]

class OTPVerifySerializer(serializers.Serializer):
    phone = serializers.CharField()
    otp = serializers.CharField(max_length=6)

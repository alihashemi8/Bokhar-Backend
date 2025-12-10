import re

from rest_framework import serializers

from .models import User

from django.contrib.auth import authenticate


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["fullname", "phone", "id"]


class RegisterSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField( write_only=True)

    class Meta:
        model = User
        fields = ["fullname", "phone", "password", "password2"]
        extra_kwargs = {"password": {"write_only": True}}

    def validate(
        self, attrs
    ):  # برای چک کردن پسورد = پسورد حداقل 6حرفی و شامل حروف و عدد باشد
        password = attrs.get("password")
        password2 = attrs.get("password2")
        if password != password2:
                raise serializers.ValidationError({"پیام": "رمز عبور و تکرار رمز عبور یکسان نیست"})

        if len(password) < 6:
             raise serializers.ValidationError({"پیام":"حداقل طول رمز باید 6 باشد"})

                #  حداقل یک عدد و حروف
        if not re.search(r"\d", password) and not re.search(r"[A-Z]", password):
            raise serializers.ValidationError({"پیام":"رمز باید حداقل شامل یک عدد و حروف باشد"})

        return attrs

    # ساختن کاربر جدید
    def create(self, validated_data):
        validated_data.pop("password2")
        phone = validated_data.get("phone")# نیازی نیست داخل پایگاه داده ذخیره بشه
        user = User.objects.filter(phone=phone)
        if user.exists():
           raise serializers.ValidationError({"پیام":"قبلا ثبت نام کرده ای"})
        user = User.objects.create_user(
            phone=phone,
            fullname=validated_data["fullname"],
            password=validated_data["password"],
        )
        return user

class LoginSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["phone", "password"]
        extra_kwargs = {"password": {"write_only": True}}

    def validate(self, attrs):
        phone = attrs.get("phone")
        password = attrs.get("password")
        user = authenticate(phone=phone, password=password)
        if user is None:
            raise serializers.ValidationError({"پیام":"رمز عبور یا شماره تلفن اشتباه است"})
        else:
           attrs["user"] = user
        return attrs


class OTPVerifySerializer(serializers.Serializer):
    phone = serializers.CharField()
    otp = serializers.CharField(max_length=6)

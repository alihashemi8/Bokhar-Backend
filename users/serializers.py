import re

from django.contrib.auth import authenticate
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["fullname", "phone", "id"]


class RegisterSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ["fullname", "phone", "password"]
        extra_kwargs = {"password": {"write_only": True}}

    def validate(
        self, attrs
    ):  # برای چک کردن پسورد = پسورد حداقل 6حرفی و شامل حروف و عدد باشد
        password = attrs.get("password")
        phone = attrs.get("phone")
        if len(phone) != 11:
            raise serializers.ValidationError({"پیام": "شماره تلفن 11 رقم است"})

        if len(password) < 6:
            raise serializers.ValidationError({"پیام": "حداقل طول رمز باید 6 باشد"})

            #  حداقل یک عدد و حروف
        if not re.search(r"\d", password) and not re.search(r"[A-Z]", password):
            raise serializers.ValidationError(
                {"پیام": "رمز باید حداقل شامل یک عدد و حروف باشد"}
            )

        return attrs

    # ساختن کاربر جدید
    def create(self, validated_data):
        phone = validated_data.get("phone")  # نیازی نیست داخل پایگاه داده ذخیره بشه
        user = User.objects.filter(phone=phone)
        if user.exists():
            raise serializers.ValidationError({"پیام": "قبلا ثبت نام کرده ای"})
        user = User.objects.create_user(
            phone=phone,
            fullname=validated_data["fullname"],
            password=validated_data["password"],
        )
        return user


class LoginSerializer(serializers.Serializer):
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        phone = attrs.get("phone")
        password = attrs.get("password")
        # request = self.context.get("request")  # مهم!
        print("phone", phone, "pass", password)
        user = authenticate(phone=phone, password=password)
        if user is None:
            raise serializers.ValidationError(
                {"پیام": "رمز عبور یا شماره تلفن اشتباه است"}
            )
        else:
            attrs["user"] = user
        return attrs


class OTPVerifySerializer(serializers.Serializer):
    phone = serializers.CharField()
    otp = serializers.CharField(max_length=6)

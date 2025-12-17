# users/views.py
import json

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from .models import *
from .serializers import *
from .tasks import *
from .utils import *


def _set_jwt_cookies(response, refresh_token: RefreshToken):
    """
    ست کردن cookie های access و refresh
    از تنظیمات settings.SIMPLE_JWT استفاده می‌کنیم
    """
    access_token = str(refresh_token.access_token)
    cookie_secure = getattr(settings, "SIMPLE_JWT", {}).get(
        "AUTH_COOKIE_SECURE", False
    )  # وقتی دیپلوی کردیم true بذاریم
    cookie_samesite = getattr(settings, "SIMPLE_JWT", {}).get(
        "AUTH_COOKIE_SAMESITE", "Lax"  # در محیط توسعه simlite
    )
    access_max_age = int(
        getattr(settings, "SIMPLE_JWT", {}).get("ACCESS_TOKEN_LIFETIME_SECONDS", 3600)
    )
    refresh_max_age = int(
        getattr(settings, "SIMPLE_JWT", {}).get(
            "REFRESH_TOKEN_LIFETIME_SECONDS", 7 * 24 * 3600
        )
    )

    # access cookie
    response.set_cookie(
        key=getattr(settings, "SIMPLE_JWT", {}).get("AUTH_COOKIE", "access"),
        value=access_token,
        httponly=True,
        secure=cookie_secure,
        samesite=cookie_samesite,
        max_age=access_max_age,
        path="/",
    )
    # refresh cookie
    response.set_cookie(
        key=getattr(settings, "SIMPLE_JWT", {}).get("AUTH_COOKIE_REFRESH", "refresh"),
        value=str(refresh_token),
        httponly=True,
        secure=cookie_secure,
        samesite=cookie_samesite,
        max_age=refresh_max_age,
        path="/",
    )


class SendOTPView(APIView):
    serializer_class = SendOTPSerializer

    def post(self, request):
        serializers = self.serializer_class(data=request.data)
        if serializers.is_valid():
            phone = serializers.validated_data["phone"]
            code = generateOTP(phone)
            send_sms.delay(phone, code)
            return Response({"detail": "کد ارسال شد"}, status=status.HTTP_200_OK)
        else:
            return Response(serializers.errors, status=status.HTTP_400_BAD_REQUEST)


# csf_token = زمانی نیاز است که توکن ها داخل کوکی باشد کاربر داخل سایت باشد


@method_decorator(csrf_exempt, name="dispatch")
class RegisterOTPView(APIView):
    serializer_class = RegisterOTPSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            response = Response(
                {
                    "phone": user.phone,
                    "fullname": user.fullname,
                    "user": user.is_admin,
                    "message": "خوش امدید",
                },
                status=200,
            )
            _set_jwt_cookies(response, refresh)
            return response
        else:
            return Response(serializer.errors)


@method_decorator(csrf_exempt, name="dispatch")
class LoginOTPView(APIView):
    serializer_class = LoginOTPSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]
            refresh = RefreshToken.for_user(user)
            response = Response(
                {
                    "phone": user.phone,
                    "fullname": user.fullname,
                    "user": user.is_admin,
                    "message": "خوش امدید",
                },
                status=200,
            )
            _set_jwt_cookies(response, refresh)
            return response
        else:
            return Response(serializer.errors)


@method_decorator(csrf_protect, name="dispatch")
class LoginPasswordView(APIView):
    serializer_class = LoginPasswordSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            user = serializer.validated_data["user"]
            response = Response(
                {
                    "phone": user.phone,
                    "fullname": user.fullname,
                    "user": user.is_admin,
                    "message": "خوش امدید",
                },
                status=200,
            )
            print(user.phone, user.fullname)
            _set_jwt_cookies(response, refresh_token=RefreshToken.for_user(user))
            return response
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.token_blacklist.models import (BlacklistedToken,
                                                             OutstandingToken)
from rest_framework_simplejwt.tokens import RefreshToken


@method_decorator(csrf_protect, name="dispatch")
class LogOutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        # حذف کوکی‌ها
        response = Response(
            {"status": "ok", "message": "خروج انجام شد"}, status=status.HTTP_200_OK
        )

        # اسم کوکی‌ها
        access_token_cookie_name = settings.SIMPLE_JWT.get("AUTH_COOKIE", "access")
        refresh_token_cookie_name = settings.SIMPLE_JWT.get(
            "AUTH_COOKIE_REFRESH", "refresh"
        )

        # حذف کوکی‌ها با اسم
        response.delete_cookie(access_token_cookie_name, path="/")
        response.delete_cookie(refresh_token_cookie_name, path="/")

        return response


@method_decorator(csrf_protect, name="dispatch")
class RefreshTokenView(APIView):

    def post(self, request):
        refresh_token_name = settings.SIMPLE_JWT.get("AUTH_COOKIE_REFRESH", "refresh")
        refresh_cookie = request.COOKIES.get(refresh_token_name)

        if refresh_cookie is None:
            return Response(
                {"detail": "رفرش توکن یافت نشد، لطفاً دوباره وارد شوید."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            refresh = RefreshToken(refresh_cookie)
            access_token = str(refresh.access_token)

            response = Response({"access": access_token}, status=200)

            response.set_cookie(
                key=settings.SIMPLE_JWT.get("AUTH_COOKIE", "access"),
                value=access_token,
                httponly=True,
                secure=False,  # در production مقدار True
                samesite="Lax",
                path="/",
            )

            return response

        except Exception:
            return Response({"detail": "رفرش توکن معتبر نیست"}, status=401)


@method_decorator(csrf_protect, name="dispatch")
class VerifyTokenView(APIView):
    def post(self, request):
        access_token_jwt = settings.SIMPLE_JWT.get("AUTH_COOKIE", "access")
        access_token_cookie = request.COOKIES.get(access_token_jwt)
        if access_token_cookie is None:
            return Response({"detail": "ارور"}, status=400)
        try:
            AccessToken(access_token_cookie)
            return Response({"detail": "توکن معتبر"}, status=200)
        except Exception as e:
            return Response(status=401)


class EditFullNameView(APIView):
    serializer_class = EditFullNameSerializer
    permission_classes = (IsAuthenticated,)

    def put(self, request):
        user = request.user
        serializer = self.serializer_class(
            user, data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "اطلاعات با موفقیت بروزرسانی شد"})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EditPasswordView(APIView):
    serializer_class = EditPasswordSerializer
    permission_classes = (IsAuthenticated,)

    def put(self, request):
        user = request.user
        serializer = self.serializer_class(
            user, data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "اطلاعات با موفقیت بروزرسانی شد"})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        cookie_name = getattr(settings.SIMPLE_JWT, "AUTH_COOKIE", "access")
        raw_token = request.COOKIES.get(cookie_name)
        if raw_token is None:
            return None
        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token

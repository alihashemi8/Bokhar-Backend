import json

from django.conf import settings
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.csrf import ensure_csrf_cookie

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

from django.contrib.auth import get_user_model

from .models import *
from .serializers import *
from .tasks import *
from .utils import *


User = get_user_model()

# ------------------------------------------------------------------
# JWT Cookie Helper
# ------------------------------------------------------------------

def _set_jwt_cookies(response: Response, refresh_token: RefreshToken) -> Response:
    simple_jwt = getattr(settings, "SIMPLE_JWT", {})

    cookie_secure = simple_jwt.get("AUTH_COOKIE_SECURE", False)
    cookie_samesite = simple_jwt.get("AUTH_COOKIE_SAMESITE", "Lax")

    access_token = str(refresh_token.access_token)
    refresh_token_str = str(refresh_token)

    response.set_cookie(
        key=simple_jwt.get("AUTH_COOKIE", "access"),
        value=access_token,
        httponly=True,
        secure=cookie_secure,
        samesite=cookie_samesite,
        max_age=int(simple_jwt.get("ACCESS_TOKEN_LIFETIME_SECONDS", 3600)),
        path="/",
    )

    response.set_cookie(
        key=simple_jwt.get("AUTH_COOKIE_REFRESH", "refresh"),
        value=refresh_token_str,
        httponly=True,
        secure=cookie_secure,
        samesite=cookie_samesite,
        max_age=int(simple_jwt.get("REFRESH_TOKEN_LIFETIME_SECONDS", 604800)),
        path="/",
    )

    return response


# ------------------------------------------------------------------
# OTP
# ------------------------------------------------------------------

@method_decorator(csrf_exempt, name="dispatch")
class SendOTPView(APIView):
    serializer_class = SendOTPSerializer
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data["phone"]
            code = generate_otp(phone)
            send_sms.delay(phone, code)
            return Response({"detail": "کد ارسال شد"}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name="dispatch")
class RegisterOTPView(APIView):
    serializer_class = RegisterOTPSerializer
    permission_classes = (AllowAny,)

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
                    "role": user.role,
                    "message": "خوش آمدید",
                },
                status=status.HTTP_200_OK,
            )

            return _set_jwt_cookies(response, refresh)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name="dispatch")
class LoginOTPView(APIView):
    serializer_class = LoginOTPSerializer
    permission_classes = (AllowAny,)

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
                    "role": user.role,
                    "message": "خوش آمدید",
                },
                status=status.HTTP_200_OK,
            )

            return _set_jwt_cookies(response, refresh)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name="dispatch")
class LoginPasswordView(APIView):
    serializer_class = LoginPasswordSerializer
    permission_classes = (AllowAny,)

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
                    "role": user.role,
                    "message": "خوش آمدید",
                },
                status=status.HTTP_200_OK,
            )

            return _set_jwt_cookies(response, refresh)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ------------------------------------------------------------------
# Logout / Refresh
# ------------------------------------------------------------------

class LogOutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        response = Response({"detail": "خروج با موفقیت انجام شد"}, status=200)

        # blacklist refresh token
        refresh_name = settings.SIMPLE_JWT.get("AUTH_COOKIE_REFRESH", "refresh")
        refresh_token = request.COOKIES.get(refresh_name)
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except (TokenError, InvalidToken):
                pass

        response.delete_cookie(settings.SIMPLE_JWT.get("AUTH_COOKIE", "access"), path="/")
        response.delete_cookie(refresh_name, path="/")


        return response



@method_decorator(csrf_protect, name="dispatch")
class RefreshTokenView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        refresh_name = settings.SIMPLE_JWT.get("AUTH_COOKIE_REFRESH", "refresh")
        old_refresh_token = request.COOKIES.get(refresh_name)

        if not old_refresh_token:
            return Response(
                {"detail": "نشست شما به پایان رسیده است"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            old_refresh = RefreshToken(old_refresh_token)

            # بررسی blacklist
            if old_refresh.blacklisted:  # <-- اضافه کن
                return Response(
                    {"detail": "نشست شما منقضی شده است"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            user = User.objects.get(id=old_refresh["user_id"])
            new_refresh = RefreshToken.for_user(user)

            try:
                old_refresh.check_blacklist()
            except TokenError:
                return Response({"detail": "نشست شما منقضی شده است"}, status=401)


            response = Response(
                {"detail": "توکن نوسازی شد"},
                status=status.HTTP_200_OK,
            )

            return _set_jwt_cookies(response, new_refresh)

        except (TokenError, InvalidToken, User.DoesNotExist):
            return Response(
                {"detail": "اعتبارنامه نامعتبر است"},
                status=status.HTTP_401_UNAUTHORIZED,
            )



# ------------------------------------------------------------------
# Protected APIs
# ------------------------------------------------------------------

class VerifyTokenView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


@method_decorator(csrf_protect, name="dispatch")
class EditFullNameView(APIView):
    serializer_class = EditFullNameSerializer
    permission_classes = (IsAuthenticated,)

    def put(self, request):
        serializer = self.serializer_class(
            request.user,
            data=request.data,
            context={"request": request},
        )
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "نام با موفقیت بروزرسانی شد"})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_protect, name="dispatch")
class EditPasswordView(APIView):
    serializer_class = EditPasswordSerializer
    permission_classes = (IsAuthenticated,)

    def put(self, request):
        serializer = self.serializer_class(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "رمز عبور با موفقیت تغییر کرد"})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@ensure_csrf_cookie
def get_csrf_token(request):
    return JsonResponse({'detail': 'CSRF cookie set'})
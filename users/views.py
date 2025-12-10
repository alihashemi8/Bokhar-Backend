# users/views.py
import json

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from rest_framework import status


from .models import OTP,User
from .utils import create_and_save_otp
from .serializers import OTPVerifySerializer,RegisterSerializer,UserSerializer,LoginSerializer


def _set_jwt_cookies(response, refresh_token: RefreshToken):
    """
    ست کردن cookie های access و refresh
    از تنظیمات settings.SIMPLE_JWT استفاده می‌کنیم
    """
    access_token = str(refresh_token.access_token)
    cookie_secure = getattr(settings, "SIMPLE_JWT", {}).get("AUTH_COOKIE_SECURE", False)
    cookie_samesite = getattr(settings, "SIMPLE_JWT", {}).get(
        "AUTH_COOKIE_SAMESITE", "Lax"
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
#csf_token = زمانی نیاز است که توکن ها داخل کوکی باشد کاربر داخل سایت باشد

class RegisterView(APIView):
    serializer_class = RegisterSerializer
    def post(self,request):
        serializer = self.serializer_class(data = request.data)#ورودی از کاربر میگیره
        if serializer.is_valid():
            user = serializer.save()
            response = JsonResponse({
                    "phone": user.phone,
                    "fullname": user.fullname,
                     "admin": user.is_admin,
                    "message": "ثبت نام با موفقیت انجام شد",
            }, status=201)

            _set_jwt_cookies(response, refresh_token=RefreshToken.for_user(user))
            return response

        else:
            return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    serializer_class = LoginSerializer
    def post(self,request):
        serializer1 = self.serializer_class(data = request.data)
        if serializer1.is_valid():
            user = serializer1.validated_data["user"]
            response = JsonResponse({
                "phone": user.phone,
                "fullname": user.fullname,
                "user":user.is_admin,
                "message": "خوش امدید",
            }, status=201)
            print(user.phone,user.fullname)
            _set_jwt_cookies(response, refresh_token=RefreshToken.for_user(user))
            return response
        else:
            return JsonResponse(serializer1.errors, status=status.HTTP_400_BAD_REQUEST)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

class LogOutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        # حذف کوکی‌ها
        response = Response({"status": "ok", "message": "خروج انجام شد"}, status=status.HTTP_200_OK)

        access_cookie_name = getattr(settings, "SIMPLE_JWT", {}).get("AUTH_COOKIE", "access")
        refresh_cookie_name = getattr(settings, "SIMPLE_JWT", {}).get("AUTH_COOKIE_REFRESH", "refresh")

        response.delete_cookie(access_cookie_name, path="/")
        response.delete_cookie(refresh_cookie_name, path="/")


        return response

@api_view(["POST"])
def logout_user(request):

    response = JsonResponse({"status": "ok", "message": "خروج انجام شد"})
    access_cookie = getattr(settings, "SIMPLE_JWT", {}).get("AUTH_COOKIE", "access")
    refresh_cookie = getattr(settings, "SIMPLE_JWT", {}).get(
        "AUTH_COOKIE_REFRESH", "refresh"
    )
    response.delete_cookie(access_cookie, path="/")
    response.delete_cookie(refresh_cookie, path="/")
    return response

@csrf_exempt
def resend_otp(request):
    if request.method != "POST":
        return JsonResponse(
            {"status": "error", "message": "Method not allowed"}, status=405
        )
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

    phone = data.get("phone")
    if not phone:
        return JsonResponse(
            {"status": "error", "message": "شماره تلفن لازم است"}, status=400
        )

    try:
        create_and_save_otp(phone, resend=True)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=429)

    return JsonResponse({"status": "ok", "message": "کد دوباره ارسال شد"})


@csrf_exempt
def verify_otp(request):

    if request.method != "POST":
        return JsonResponse(
            {"status": "error", "message": "Method not allowed"}, status=405
        )
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

    phone = data.get("phone")
    otp_received = data.get("otp")
    if not phone or not otp_received:
        return JsonResponse(
            {"status": "error", "message": "phone و otp لازم است"}, status=400
        )

    try:
        otp_obj = OTP.objects.filter(phone=phone).latest("created_at")
    except OTP.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "کدی وجود ندارد"}, status=400
        )

    if otp_obj.is_expired():
        return JsonResponse({"status": "error", "message": "کد منقضی شده"}, status=400)
    if otp_obj.attempts >= 5:
        return JsonResponse(
            {"status": "error", "message": "تلاش بیش از حد"}, status=400
        )

    entered_hash = OTP.hash_otp(otp_received)
    if entered_hash != otp_obj.otp_hash:
        otp_obj.attempts += 1
        otp_obj.save()
        return JsonResponse({"status": "error", "message": "کد اشتباه است"}, status=400)

    # موفقیت: ایجاد/واکشی کاربر
    user, created = User.objects.get_or_create(
        phone=phone, defaults={"username": phone, "is_staff": False}
    )

    # ساخت توکن
    refresh = RefreshToken.for_user(user)

    # حذف OTP
    otp_obj.delete()

    # آماده‌سازی پاسخ JSON (اطلاعات کاربر و نقش)
    role = "admin" if user.is_staff else "customer"
    response = JsonResponse(
        {
            "status": "ok",
            "message": "ورود موفق",
            "user": {
                "id": user.id,
                "phone": user.phone,
                "username": user.username,
                "role": role,
            },
        }
    )

    # ست کوکی‌ها
    _set_jwt_cookies(response, refresh)
    return response






@csrf_exempt
def login_user(request):
    """
    لاگین با phone + password (جا داره از email هم استفاده کنی)
    """
    if request.method != "POST":
        return JsonResponse(
            {"status": "error", "message": "Method not allowed"}, status=405
        )
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

    phone = data.get("phone")
    password = data.get("password")
    if not phone or not password:
        return JsonResponse(
            {"status": "error", "message": "phone و password لازم است"}, status=400
        )

    user = authenticate(request, username=phone, password=password)
    if user is None:
        return JsonResponse(
            {"status": "error", "message": "اطلاعات ورود نامعتبر است"}, status=401
        )

    refresh = RefreshToken.for_user(user)
    response = JsonResponse(
        {
            "status": "ok",
            "message": "ورود موفق",
            "user": {
                "id": user.id,
                "phone": user.phone,
                "role": "admin" if user.is_staff else "customer",
            },
        }
    )
    _set_jwt_cookies(response, refresh)
    return response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def check_auth(request):

    user = request.user
    role = "admin" if getattr(user, "is_staff", False) else "customer"
    return JsonResponse(
        {
            "isAuthenticated": True,
            "user": {
                "id": user.id,
                "phone": user.phone,
                "username": user.username,
                "role": role,
            },
        }
    )




class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        cookie_name = getattr(settings.SIMPLE_JWT, "AUTH_COOKIE", "access")
        raw_token = request.COOKIES.get(cookie_name)
        if raw_token is None:
            return None
        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token

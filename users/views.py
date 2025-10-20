# users/views.py
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model, authenticate
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .models import OTP
from .utils import create_and_save_otp
from rest_framework.response import Response

User = get_user_model()

def _set_jwt_cookies(response, refresh_token: RefreshToken):
    """
    ست کردن cookie های access و refresh
    از تنظیمات settings.SIMPLE_JWT استفاده می‌کنیم
    """
    access_token = str(refresh_token.access_token)
    cookie_secure = getattr(settings, "SIMPLE_JWT", {}).get("AUTH_COOKIE_SECURE", False)
    cookie_samesite = getattr(settings, "SIMPLE_JWT", {}).get("AUTH_COOKIE_SAMESITE", "Lax")
    access_max_age = int(getattr(settings, "SIMPLE_JWT", {}).get("ACCESS_TOKEN_LIFETIME_SECONDS", 3600))
    refresh_max_age = int(getattr(settings, "SIMPLE_JWT", {}).get("REFRESH_TOKEN_LIFETIME_SECONDS", 7*24*3600))

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

@csrf_exempt
def submit_otp(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

    phone = data.get("phone")
    if not phone:
        return JsonResponse({"status": "error", "message": "شماره تلفن لازم است"}, status=400)

    create_and_save_otp(phone)
    return JsonResponse({"status": "ok", "message": "OTP ارسال شد"})

@csrf_exempt
def resend_otp(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)
    phone = data.get("phone")
    if not phone:
        return JsonResponse({"status": "error", "message": "شماره تلفن لازم است"}, status=400)
    create_and_save_otp(phone)
    return JsonResponse({"status": "ok", "message": "کد دوباره ارسال شد"})

@csrf_exempt
def verify_otp(request):

    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

    phone = data.get("phone")
    otp_received = data.get("otp")
    if not phone or not otp_received:
        return JsonResponse({"status": "error", "message": "phone و otp لازم است"}, status=400)

    try:
        otp_obj = OTP.objects.filter(phone=phone).latest("created_at")
    except OTP.DoesNotExist:
        return JsonResponse({"status": "error", "message": "کدی وجود ندارد"}, status=400)

    if otp_obj.is_expired():
        return JsonResponse({"status": "error", "message": "کد منقضی شده"}, status=400)
    if otp_obj.attempts >= 5:
        return JsonResponse({"status": "error", "message": "تلاش بیش از حد"}, status=400)

    entered_hash = OTP.hash_otp(otp_received)
    if entered_hash != otp_obj.otp_hash:
        otp_obj.attempts += 1
        otp_obj.save()
        return JsonResponse({"status": "error", "message": "کد اشتباه است"}, status=400)

    # موفقیت: ایجاد/واکشی کاربر
    user, created = User.objects.get_or_create(
        phone=phone,
        defaults={"username": phone, "is_staff": False}
    )

    # ساخت توکن
    refresh = RefreshToken.for_user(user)

    # حذف OTP
    otp_obj.delete()

    # آماده‌سازی پاسخ JSON (اطلاعات کاربر و نقش)
    role = "admin" if user.is_staff else "customer"
    response = JsonResponse({
        "status": "ok",
        "message": "ورود موفق",
        "user": {"id": user.id, "phone": user.phone, "username": user.username, "role": role}
    })

    # ست کوکی‌ها
    _set_jwt_cookies(response, refresh)
    return response

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_me(request):
    """
    این ویو فقط برای تست هست.
    اگر JWT داخل کوکی درست باشه، کاربر لاگین‌شده رو برمی‌گردونه.
    """
    user = request.user
    return Response({
        "id": user.id,
        "phone": user.phone,
        "username": user.username,
        "role": "admin" if user.is_staff else "customer"
    })

@csrf_exempt
def register_user(request):
    """
    ثبت نام با phone + username + optional email + password
    (اگر می‌خواهی فقط OTP استفاده کنی، این endpoint لازم نیست)
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

    phone = data.get("phone")
    username = data.get("username") or phone
    password = data.get("password")
    email = data.get("email")

    if not phone or not password:
        return JsonResponse({"status": "error", "message": "phone و password لازم است"}, status=400)

    if User.objects.filter(phone=phone).exists():
        return JsonResponse({"status": "error", "message": "کاربر قبلاً وجود دارد"}, status=400)

    user = User.objects.create_user(username=username, phone=phone, email=email, password=password)
    refresh = RefreshToken.for_user(user)
    response = JsonResponse({"status": "ok", "message": "ثبت نام موفق", "user": {"id": user.id, "phone": user.phone}})
    _set_jwt_cookies(response, refresh)
    return response

@csrf_exempt
def login_user(request):
    """
    لاگین با phone + password (جا داره از email هم استفاده کنی)
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

    phone = data.get("phone")
    password = data.get("password")
    if not phone or not password:
        return JsonResponse({"status": "error", "message": "phone و password لازم است"}, status=400)

    user = authenticate(request, username=phone, password=password)
    if user is None:
        return JsonResponse({"status": "error", "message": "اطلاعات ورود نامعتبر است"}, status=401)

    refresh = RefreshToken.for_user(user)
    response = JsonResponse({"status": "ok", "message": "ورود موفق", "user": {"id": user.id, "phone": user.phone, "role": "admin" if user.is_staff else "customer"}})
    _set_jwt_cookies(response, refresh)
    return response

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def check_auth(request):

    user = request.user
    role = "admin" if getattr(user, "is_staff", False) else "customer"
    return JsonResponse({"status": "ok", "user": {"id": user.id, "phone": user.phone, "username": user.username, "role": role}})

@api_view(["POST"])
def logout_user(request):

    response = JsonResponse({"status": "ok", "message": "خروج انجام شد"})
    access_cookie = getattr(settings, "SIMPLE_JWT", {}).get("AUTH_COOKIE", "access")
    refresh_cookie = getattr(settings, "SIMPLE_JWT", {}).get("AUTH_COOKIE_REFRESH", "refresh")
    response.delete_cookie(access_cookie, path="/")
    response.delete_cookie(refresh_cookie, path="/")
    return response

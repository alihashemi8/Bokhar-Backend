# users/views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .utils import create_and_save_otp
from .models import OTP

@csrf_exempt
def submit(request):
    if request.method == "POST":
        data = json.loads(request.body)
        phone = data.get("phone")
        if not phone:
            return JsonResponse({"status": "error", "message": "phone لازم است"}, status=400)

        create_and_save_otp(phone)
        return JsonResponse({"status": "ok", "message": "OTP ارسال شد"})


@csrf_exempt
def verify_otp(request):
    if request.method == "POST":
        data = json.loads(request.body)
        phone = data.get("phone")
        otp_received = data.get("otp")

        try:
            otp_obj = OTP.objects.filter(phone=phone).latest("created_at")
        except OTP.DoesNotExist:
            return JsonResponse({"status": "error", "message": "کدی وجود ندارد"}, status=400)

        if otp_obj.is_expired():
            return JsonResponse({"status": "error", "message": "کد منقضی شده"}, status=400)

        if otp_obj.attempts >= 5:
            return JsonResponse({"status": "error", "message": "تلاش بیش از حد"}, status=400)

        entered_hash = OTP.hash_otp(otp_received)
        if entered_hash == otp_obj.otp_hash:
            otp_obj.delete()  # موفقیت → رکورد رو حذف کن
            return JsonResponse({"status": "ok", "message": "ورود موفق"})
        else:
            otp_obj.attempts += 1
            otp_obj.save()
            return JsonResponse({"status": "error", "message": "کد اشتباه است"}, status=400)


@csrf_exempt
def resend_otp(request):
    if request.method == "POST":
        data = json.loads(request.body)
        phone = data.get("phone")
        create_and_save_otp(phone)
        return JsonResponse({"status": "ok", "message": "کد دوباره ارسال شد"})

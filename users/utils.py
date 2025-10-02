# users/utils.py
import random
from .models import OTP

def create_and_save_otp(phone):
    code = f"{random.randint(0, 999999):06d}"  # مثل 123456
    otp_hash = OTP.hash_otp(code)
    OTP.objects.create(phone=phone, otp_hash=otp_hash)
    print(f"[DEV] OTP for {phone}: {code}")  # فعلاً چاپ کن
    return code

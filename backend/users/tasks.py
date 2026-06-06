from celery import shared_task


@shared_task
def send_sms(phone, code):
    print(f"OTP for {phone}: {code}")

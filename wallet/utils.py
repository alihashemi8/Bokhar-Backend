import redis
from django.db.models import Sum

from .models import WalletTransaction

r = redis.Redis(host="localhost", port=6379, db=0)


def get_balance(wallet_id):
    key = f"balance:{wallet_id}"
    balance = r.get(key)  # r.get(key) مقدار متناظر با کلید را از Redis می‌خواند.
    # مقدار متناظر از set

    if balance is None:
        balance = (
            WalletTransaction.objects.get(
                wallet_id=wallet_id, status="success"
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )
        r.set(key, balance)

    return int(balance)  # خروجی از ردیس به صورت بیت است.


def update_balance(wallet_id, delta):
    key = f"balance:{wallet_id}"
    new_balance = r.incrby(
        key, delta
    )  # این متد خودش داخل ردیس مقدار و کم و زیاد میکند.
    return new_balance

import requests

GATEWAY_URL = "https://api.zarinpal.com/pg/v4/payment/request.json"
VERIFY_URL = "https://api.zarinpal.com/pg/v4/payment/verify.json"
CALLBACK_URL = "/"


def send_request_to_gateway(payment):
    data = {
        "merchant_id": "YOUR_MERCHANT_ID",
        "amount": payment.amount,
        "callback_url": CALLBACK_URL,
        "description": f":شماره شناسه سفارش شما #{payment.order.id}",
    }
    response = requests.post(GATEWAY_URL, json=data, timeout=10)
    return response.json()


def verify_payment_gateway(payment):
    data = {
        "merchant_id": "ایدی که از زرین پال میگیرم",
        "amount": payment.amount,
        "authority": payment.authority,
    }
    response = requests.post(VERIFY_URL, json=data, timeout=10)
    return response.json()

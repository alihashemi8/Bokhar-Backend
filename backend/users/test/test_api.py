import pytest
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient

from backend.users.models import User


@pytest.fixture  # برای کدهای تکراری
def api_client():
    return APIClient()


def test_sent_otp_api(api_client):
    url = reverse("users:otp")
    data = {"phone": "09125638817"}
    response = api_client.post(url, data)
    assert response.status_code == 200


@pytest.mark.django_db
def test_login_otp(api_client):
    phone = "09125638817"
    code = "123456"
    User.objects.create_user(phone=phone, fullname="hasti")
    url = reverse("users:login_otp")
    cache.set(f"otp:{phone}", make_password(code), timeout=120)
    data = {"phone": phone, "otp": "123456"}
    response = api_client.post(url, data)
    print(response.data)
    assert response.status_code == 200


@pytest.mark.django_db
def test_login_password(api_client):
    url = reverse("users:login")
    phone = "09352628095"
    password = "hasti84"
    User.objects.create_user(phone=phone, fullname="hasti", password=password)
    data = {"phone": phone, "password": password}
    response = api_client.post(url, data)
    print(response.data)
    assert response.status_code == 200


@pytest.mark.django_db
def test_register_otp(api_client):


    phone = "09125558817"
    cache.set(f"otp:{phone}", make_password("123456"), timeout=120)
    url = reverse("users:register")
    data = {"phone": phone, "fullname": "hasti", "otp": "123456"}

    response = api_client.post(url, data=data)
    assert response.status_code == 200

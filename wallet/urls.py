from .views import *
from django.urls import path

app_name = 'wallet'
urlpatterns = [
    path("verify/payment/wallet",verify_wallet_charge_view,name = 'verify_charge'),
    path("verify/payment",verify_order_payment_view,name = 'payment'),
    path("order/payment",initiate_order_payment_view,name = "order"),
    path("wallet/payment",initiate_wallet_charge_view,name = "wallet_charge"),
]
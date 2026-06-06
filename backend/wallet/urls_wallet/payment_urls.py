# wallet/report_urls.py
from django.urls import path

from ..views.setting_payment_views import *  # ایمپورت ویوها از فایل views موجود در همین پوشه
from ..views.views import *

urlpatterns = [
    # پرداخت از طریق کیف پول
    path("wallet-payment/", WalletPayment.as_view(), name="wallet-payment"),
    # شارژ کیف پول (شروع پرداخت بانکی)
    path("wallet/charge/", WalletChargeView.as_view(), name="wallet-charge"),
    # تأیید شارژ کیف پول (بازگشت از درگاه)
    path(
        "payment/verify/",  # نامی که در reverse('payment-verify') استفاده شده
        VerifyPaymentView.as_view(),
        name="payment-verify",
    ),
    # توجه: عبارت VeryfiChargeWalletView ظاهراً برای تأیید شارژ کیف پول است.
    # اما در کد WalletChargeView از reverse('payment-verify') استفاده می‌کند
    # که به VerifyPaymentView اشاره دارد.
    # بنابراین VeryfiChargeWalletView ممکن است یک endpoint جداگانه نباشد
    # یا اینکه به اشتباه نامگذاری شده. در صورت نیاز می‌توان مسیر آن را نیز اضافه کرد:
    # path('wallet/charge/verify/',    VeryfiChargeWalletView.as_view(), name='wallet-charge-verify'),
    # استرداد سفارش به کیف پول
    path("orders/<int:id>/refund/", RefundOrderView.as_view(), name="order-refund"),
    # شروع پرداخت عادی (درگاه)
    path("payment/initiate/", PaymentInitiateView.as_view(), name="payment-initiate"),
    # انتقال وجه از کیف پول به حساب بانکی
    path(
        "payment/refund-to-account/",
        RefundMoneyToAccount.as_view(),
        name="withdraw-to-bank",
    ),
]

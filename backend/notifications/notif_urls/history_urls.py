# notification/report_urls.py (یا اپ مربوطه، مثلاً discount یا wallet)
from django.urls import path

from ..views import *

urlpatterns = [
    # تاریخچه تراکنش‌های کیف پول
    # path(
    #    'wallet-transactions/',
    #   HistoryWalletTransaction.as_view(),
    #  name='wallet-transaction-history'
    # ),
    # تاریخچه تراکنش‌های کیف پول
    # path(
    #    'wallet/',
    #   walletDisplay.as_view(),
    #  name='wallet-transaction-history'
    # ),
    # تاریخچه سفارش‌ها
    # تاریخچه سفارش‌ها
    path("orders/history/", HistoryOrder.as_view(), name="order-history"),
    # جزئیات یک سفارش
    path(
        "order/history/<int:id>/",
        HistoryOrderDetail.as_view(),
        name="order-history-detail",
    ),
    # لیست کوپن‌های کاربر
    path("coupons/", CouponListOrder.as_view(), name="user-coupon-list"),
    # تخفیف‌های فعال (نیازمند احراز هویت)
    path("discounts/", DiscountList.as_view(), name="discount-list"),
    # همه تخفیف‌های فعال (عمومی، بدون احراز هویت)
    path("discounts/all/", DiscountListall.as_view(), name="discount-list-all"),
]

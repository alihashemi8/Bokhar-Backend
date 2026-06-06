from django.urls import path
from ..order_admin_view import *

urlpatterns = [
    # ---------- لیست سفارش‌ها بر اساس وضعیت ----------
    path('list/paid/',  PaidStatusView.as_view(), name='list-paid'),
    path('list/washing/',  WashStatusView.as_view(), name='list-washing'),
    path('list/delivered/',  DeliveryStatusView.as_view(), name='list-delivered'),
    path('list/canceled/',  CancelStatusView.as_view(), name='list-canceled'),
    path('list/returned/',  ReturnStatusView.as_view(), name='list-returned'),

    # ---------- جستجوی سفارش ----------
    path('search/',  SearchOrderView.as_view(), name='search'),

    # ---------- تغییر وضعیت سفارش‌ها (عملیات دسته‌جمعی) ----------
    path('status/pick/',  UpdateStatusPickView.as_view(), name='status-to-pick'),
    path('status/washing/',  UpdateStatusWashingView.as_view(), name='status-to-washing'),
    path('status/delivery/',  UpdateStatusDeliveryView.as_view(), name='status-to-delivery'),

    # ---------- تاریخچه وضعیت یک سفارش ----------
    path('<int:order_id>/history/',  OrderStatusHistoryView.as_view(), name='order-history'),
]